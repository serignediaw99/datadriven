"""
Walk-forward backtest: fitted Dixon-Coles vs. the current Elo heuristic.

For each cutoff date we fit on matches strictly before it and score the next
window of matches out-of-sample with three proper scoring rules:

  - multiclass log-loss      (lower = better)
  - Brier score (3-class)    (lower = better)
  - Ranked Probability Score (ordinal H/D/A; the standard for football)

Baselines:
  - "elo"   : point-in-time world-football Elo computed from the same history,
              mapped to goals with the EXACT current heuristic (ratings.py).
  - "dc"    : the time-weighted Dixon-Coles model (fit_dixon_coles.fit_model).

Run:  python -m app.models.backtest
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.data.results_history import load_results_sync
from app.models.fit_dixon_coles import fit_model, FittedModel, LAMBDA_CLIP
from app.models.dixon_coles import _tau

# Current heuristic constants (mirrors app/models/ratings.py).
ELO_BASE_RATE = 1.15
ATTACK_SCALE = 0.40
DEFENSE_SCALE = 0.30
ELO_UNIT = 200.0

ELO_HFA = 65.0       # home-field advantage in Elo points
ELO_K = 40.0         # update factor
MAX_GOALS = 10


# ---------------------------------------------------------------- point-in-time Elo
def compute_elo(df: pd.DataFrame) -> dict[str, float]:
    """Standard world-football Elo over the given (chronological) matches."""
    elo: dict[str, float] = {}
    base = 1500.0
    for home, away, hs, as_, neutral in zip(
        df["home_team"], df["away_team"], df["home_score"],
        df["away_score"], df["neutral"]
    ):
        rh = elo.get(home, base)
        ra = elo.get(away, base)
        hfa = 0.0 if neutral else ELO_HFA
        exp_h = 1.0 / (1.0 + 10 ** (-(rh + hfa - ra) / 400.0))
        if hs > as_:
            sh = 1.0
        elif hs < as_:
            sh = 0.0
        else:
            sh = 0.5
        gd = abs(hs - as_)
        mov = math.sqrt(max(gd, 1))  # goal-difference weighting
        delta = ELO_K * mov * (sh - exp_h)
        elo[home] = rh + delta
        elo[away] = ra - delta
    return elo


# ---------------------------------------------------------------- W/D/L predictors
def _poisson_pmf(lam: float, kmax: int) -> np.ndarray:
    ks = np.arange(kmax + 1)
    return np.exp(-lam) * lam**ks / np.array([math.factorial(k) for k in ks])


def wdl_from_lambdas(lam_h: float, lam_a: float, rho: float = 0.0) -> tuple[float, float, float]:
    """P(home win), P(draw), P(away win) from two Poisson rates + DC tau."""
    lam_h = min(max(lam_h, 1e-6), LAMBDA_CLIP)
    lam_a = min(max(lam_a, 1e-6), LAMBDA_CLIP)
    ph = _poisson_pmf(lam_h, MAX_GOALS)
    pa = _poisson_pmf(lam_a, MAX_GOALS)
    mat = np.outer(ph, pa)
    if rho:
        for g1 in (0, 1):
            for g2 in (0, 1):
                mat[g1, g2] *= _tau(g1, g2, lam_h, lam_a, rho)
    mat /= mat.sum()
    p_home = float(np.tril(mat, -1).sum())
    p_draw = float(np.trace(mat))
    p_away = float(np.triu(mat, 1).sum())
    return p_home, p_draw, p_away


def predict_dc(model: FittedModel, home, away, neutral) -> tuple[float, float, float]:
    lam_h, lam_a = model.goal_rates(home, away, home_field=not neutral)
    return wdl_from_lambdas(lam_h, lam_a, model.rho)


def predict_elo(elo: dict, home, away, neutral) -> tuple[float, float, float]:
    if not elo:
        return 1 / 3, 1 / 3, 1 / 3
    avg = sum(elo.values()) / len(elo)
    rh = elo.get(home, avg) + (0.0 if neutral else ELO_HFA)
    ra = elo.get(away, avg)
    dh = (rh - avg) / ELO_UNIT
    da = (ra - avg) / ELO_UNIT
    lam_h = ELO_BASE_RATE * math.exp(ATTACK_SCALE * dh - DEFENSE_SCALE * da)
    lam_a = ELO_BASE_RATE * math.exp(ATTACK_SCALE * da - DEFENSE_SCALE * dh)
    return wdl_from_lambdas(lam_h, lam_a, 0.0)


# ---------------------------------------------------------------- scoring rules
def _outcome(hs, as_) -> int:
    return 0 if hs > as_ else (1 if hs == as_ else 2)  # H, D, A


def log_loss(p, y) -> float:
    return -math.log(max(p[y], 1e-12))


def brier(p, y) -> float:
    return sum((p[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(3))


def rps(p, y) -> float:
    # ordinal cumulative: H, D, A
    obs = [0.0, 0.0, 0.0]
    obs[y] = 1.0
    cp = cy = 0.0
    total = 0.0
    for i in range(2):  # r-1 = 2 cumulative steps
        cp += p[i]
        cy += obs[i]
        total += (cp - cy) ** 2
    return total / 2.0


@dataclass
class Scores:
    n: int
    logloss: float
    brier: float
    rps: float


def _aggregate(rows) -> Scores:
    arr = np.array(rows)
    return Scores(len(rows), arr[:, 0].mean(), arr[:, 1].mean(), arr[:, 2].mean())


# ---------------------------------------------------------------- driver
def run_backtest(
    df: pd.DataFrame,
    cutoffs: list[str],
    window_days: int = 365,
    competitive_only: bool = True,
    half_life_years: float = 2.0,
    reg: float = 0.05,
):
    dc_rows, elo_rows = [], []
    per_cut = []
    for c in cutoffs:
        cut = pd.Timestamp(c)
        train = df[df["date"] < cut]
        test = df[(df["date"] >= cut) & (df["date"] < cut + pd.Timedelta(days=window_days))]
        if competitive_only:
            test = test[~test["tournament"].str.contains("Friendly", case=False, na=False)]
        if len(train) < 1000 or len(test) == 0:
            continue

        model = fit_model(train, as_of=cut, half_life_years=half_life_years, reg=reg)
        elo = compute_elo(train.sort_values("date"))

        dc_c, elo_c = [], []
        for home, away, hs, as_, neutral in zip(
            test["home_team"], test["away_team"], test["home_score"],
            test["away_score"], test["neutral"]
        ):
            y = _outcome(hs, as_)
            pdc = predict_dc(model, home, away, neutral)
            pelo = predict_elo(elo, home, away, neutral)
            dc_c.append([log_loss(pdc, y), brier(pdc, y), rps(pdc, y)])
            elo_c.append([log_loss(pelo, y), brier(pelo, y), rps(pelo, y)])
        dc_rows += dc_c
        elo_rows += elo_c
        per_cut.append((c, _aggregate(dc_c), _aggregate(elo_c)))

    dc = _aggregate(dc_rows)
    elo = _aggregate(elo_rows)

    print(f"\n{'cutoff':>12} {'N':>5} | {'DC logloss':>11} {'Elo logloss':>11} | "
          f"{'DC rps':>8} {'Elo rps':>8}")
    print("-" * 70)
    for c, d, e in per_cut:
        print(f"{c:>12} {d.n:>5} | {d.logloss:>11.4f} {e.logloss:>11.4f} | "
              f"{d.rps:>8.4f} {e.rps:>8.4f}")
    print("-" * 70)
    print(f"{'OVERALL':>12} {dc.n:>5} | {dc.logloss:>11.4f} {elo.logloss:>11.4f} | "
          f"{dc.rps:>8.4f} {elo.rps:>8.4f}")
    print(f"\nBrier   — DC {dc.brier:.4f}  vs  Elo {elo.brier:.4f}")
    improvement = (elo.logloss - dc.logloss) / elo.logloss * 100
    print(f"\nLog-loss improvement of DC over Elo heuristic: {improvement:+.2f}%")
    print("ACCEPTANCE:", "PASS" if (dc.logloss < elo.logloss and dc.rps < elo.rps) else "FAIL")
    return dc, elo


if __name__ == "__main__":
    df = load_results_sync()
    run_backtest(
        df,
        cutoffs=[
            "2018-06-01",  # pre-2018 WC
            "2021-06-01",  # pre-Euro 2020(21)/Copa
            "2022-11-01",  # pre-2022 WC
            "2024-06-01",  # pre-Euro 2024 / Copa
            "2025-06-01",
        ],
        window_days=365,
    )
