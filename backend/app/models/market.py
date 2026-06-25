"""
Bookmaker-odds de-vigging and rating-level blend (Phase 2).

Two pure-function stages:

1. *De-vig* — turn decimal odds into probabilities. Each bookmaker's prices imply
   probabilities ``1/price`` that sum to more than 1 (the overround / "vig"). We
   strip the vig by normalizing within each book, then average across books for a
   consensus. Done for both the outright winner market and per-match h2h.

2. *Blend* — fold the consensus outright (champion) probabilities into the model at
   the **rating** level so every downstream odd (group, R16, …, Winner) stays
   internally consistent. We invert each market champion probability into a model
   "strength" using the model's *own* champion-prob↔strength relationship (a robust
   1-D regression over the simulated teams), then take a weighted average of model
   and market strength. Because a uniform strength shift cancels in the Poisson
   means, only *relative* strengths move — exactly what a calibration blend should do.

The blend is applied by re-simulating with the adjusted ``TeamParams``; this module
only computes the adjusted params.
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace

import numpy as np
from scipy.optimize import minimize

from app.models.ratings import TeamParams

log = logging.getLogger(__name__)


# --- De-vig --------------------------------------------------------------------

def devig_outrights(payload: list) -> dict[str, float]:
    """
    Consensus de-vigged champion probability per team from the outrights payload.

    Each bookmaker is de-vigged independently (normalize 1/price over the teams it
    prices), then averaged across books. Teams a book omits are treated as ~0 for
    that book, which is correct for tournament longshots.
    """
    if not payload:
        return {}
    per_book: list[dict[str, float]] = []
    for event in payload:
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                raw = {
                    o["name"]: 1.0 / o["price"]
                    for o in market.get("outcomes", [])
                    if o.get("price", 0) > 0
                }
                total = sum(raw.values())
                if total > 0:
                    per_book.append({k: v / total for k, v in raw.items()})
    if not per_book:
        return {}
    teams = set().union(*per_book)
    n = len(per_book)
    return {t: sum(b.get(t, 0.0) for b in per_book) / n for t in teams}


def devig_h2h(payload: list) -> list[dict]:
    """
    Consensus de-vigged 1X2 probabilities per upcoming match.

    Returns a list of ``{home, away, commence_time, p_home, p_draw, p_away}``.
    """
    out: list[dict] = []
    for event in payload or []:
        home = event.get("home_team")
        away = event.get("away_team")
        if not home or not away:
            continue
        ph, pd, pa, n = 0.0, 0.0, 0.0, 0
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                prices = {o["name"]: o["price"] for o in market.get("outcomes", [])
                          if o.get("price", 0) > 0}
                if home not in prices or away not in prices or "Draw" not in prices:
                    continue
                ih, ia, idr = 1 / prices[home], 1 / prices[away], 1 / prices["Draw"]
                tot = ih + ia + idr
                ph += ih / tot
                pa += ia / tot
                pd += idr / tot
                n += 1
        if n:
            out.append({
                "home": home, "away": away,
                "commence_time": event.get("commence_time"),
                "p_home": ph / n, "p_draw": pd / n, "p_away": pa / n,
            })
    return out


# --- Rating-level blend --------------------------------------------------------

def blend_team_params(
    team_params: dict[str, TeamParams],
    model_champ_probs: dict[str, float],
    market_champ_probs: dict[str, float],
    w: float = 0.7,
    clip: float = 1.5,
) -> dict[str, TeamParams]:
    """
    Return ``TeamParams`` nudged toward the market's champion probabilities.

    ``w`` is the weight on the model (1.0 = pure model, 0.0 = pure market strength).
    Only teams present in both probability maps are adjusted; others pass through.

    Strength is ``alpha + beta``; we invert market champion prob into that scale via
    a least-squares fit of ``log(model champ prob) ~ a + b*strength`` over the
    simulated field, then split the strength delta evenly across alpha/beta so the
    attack/defense balance is preserved and only overall strength moves.
    """
    shared = [
        t for t in market_champ_probs
        if t in team_params and model_champ_probs.get(t, 0.0) > 0.0
    ]
    if len(shared) < 4:
        log.info("Odds blend skipped: only %d shared teams", len(shared))
        return team_params

    strength = np.array([team_params[t].alpha + team_params[t].beta for t in shared])
    log_pmod = np.array([math.log(model_champ_probs[t]) for t in shared])

    # Robust-ish 1-D fit: log champ prob increases with strength. Guard a flat fit.
    b, a = np.polyfit(strength, log_pmod, 1)
    if not np.isfinite(b) or b <= 1e-6:
        log.warning("Odds blend skipped: degenerate strength->prob slope (%.4g)", b)
        return team_params

    s_lo, s_hi = strength.min() - clip, strength.max() + clip
    blended = dict(team_params)
    moved = 0
    for t in shared:
        s_model = team_params[t].alpha + team_params[t].beta
        s_market = (math.log(market_champ_probs[t]) - a) / b
        s_market = min(max(s_market, s_lo), s_hi)
        s_final = w * s_model + (1.0 - w) * s_market
        half = 0.5 * (s_final - s_model)
        if abs(half) > 1e-6:
            p = team_params[t]
            blended[t] = replace(p, alpha=p.alpha + half, beta=p.beta + half)
            moved += 1
    log.info(
        "Odds blend applied to %d teams (w=%.2f, slope b=%.3f)", moved, w, b
    )
    return blended


# --- Per-match (h2h) blend -----------------------------------------------------
# The outright blend above can't calibrate a match between two no-hope teams (both
# have ~0 title probability). The h2h market can: it directly prices each upcoming
# fixture's win/draw/loss. We convert those into goal rates (lambdas) the sim can
# sample, by finding the independent-Poisson (lambda_home, lambda_away) whose W/D/L
# best matches the de-vigged market, then blend with the model's lambdas in log space.

_MAX_GOALS = 10
_FACT = np.array([math.factorial(k) for k in range(_MAX_GOALS + 1)], dtype=np.float64)


def _poisson_pmf(lam: float) -> np.ndarray:
    k = np.arange(_MAX_GOALS + 1)
    return np.exp(-lam) * lam ** k / _FACT


def wdl_from_lambdas(lam1: float, lam2: float) -> tuple[float, float, float]:
    """(P home win, P draw, P away win) under independent Poisson, capped goals."""
    m = np.outer(_poisson_pmf(lam1), _poisson_pmf(lam2))  # m[i,j] = P(home=i, away=j)
    p_draw = float(np.trace(m))
    p_home = float(np.tril(m, -1).sum())  # home goals > away goals
    p_away = float(np.triu(m, 1).sum())
    return p_home, p_draw, p_away


def solve_match_lambdas(
    p_home_win: float, p_draw: float, lam1_start: float, lam2_start: float
) -> tuple[float, float]:
    """
    Find independent-Poisson (lambda_home, lambda_away) whose W/D/L best matches the
    de-vigged market (p_home_win, p_draw). Warm-started from the model's lambdas.
    """
    target = np.array([p_home_win, p_draw])

    def obj(x: np.ndarray) -> float:
        l1, l2 = math.exp(x[0]), math.exp(x[1])
        pw, pd, _ = wdl_from_lambdas(l1, l2)
        return (pw - target[0]) ** 2 + (pd - target[1]) ** 2

    x0 = np.log([max(lam1_start, 1e-2), max(lam2_start, 1e-2)])
    res = minimize(obj, x0, method="Nelder-Mead",
                   options={"xatol": 1e-3, "fatol": 1e-7, "maxiter": 400})
    return float(math.exp(res.x[0])), float(math.exp(res.x[1]))


def blend_match_lambdas(
    model_lam1: float, model_lam2: float,
    p_home_win: float, p_draw: float,
    w_model: float,
) -> tuple[float, float]:
    """
    Blend the model's goal rates toward the market-implied ones (log-space, so a
    uniform scaling is geometric). ``w_model`` is the weight on the model
    (0 = pure market, 1 = pure model).
    """
    mk1, mk2 = solve_match_lambdas(p_home_win, p_draw, model_lam1, model_lam2)
    lam1 = math.exp(w_model * math.log(model_lam1) + (1 - w_model) * math.log(mk1))
    lam2 = math.exp(w_model * math.log(model_lam2) + (1 - w_model) * math.log(mk2))
    return lam1, lam2


def h2h_by_pair(payload: list) -> dict[frozenset, dict]:
    """Index de-vigged h2h games by the unordered team pair for quick lookup."""
    out: dict[frozenset, dict] = {}
    for g in devig_h2h(payload):
        out[frozenset((g["home"], g["away"]))] = g
    return out
