"""
Fit a time-weighted Dixon-Coles team-strength model from historical results.

Each team gets an independent attack (`atk`) and defense (`def`) parameter on the
log-goal scale. A global base rate `mu`, home advantage `gamma`, and low-score
correction `rho` are fit jointly. Recent matches count more via exponential time
decay (`half_life_years`).

Goal rates for a match between home H and away A:

    lambda_home = exp(mu + atk[H] - def[A] + gamma * is_home)
    lambda_away = exp(mu + atk[A] - def[H])

The attack/defense/home parameters are estimated by maximising a *weighted*
Poisson log-likelihood with a ridge penalty (which both regularises thin teams
and pins down the otherwise-degenerate overall level). This has an analytic
gradient, so the ~2*N-team problem solves in a few seconds over ~50k matches.
`rho` is then estimated by a cheap 1-D profile using the Dixon-Coles tau, exactly
as in Dixon & Coles (1997). tau is reused from app.models.dixon_coles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar

from app.models.dixon_coles import _tau

LAMBDA_CLIP = 30.0  # cap goal rate to keep exp() well-behaved


@dataclass
class FittedModel:
    teams: list[str]
    attack: dict[str, float]
    defense: dict[str, float]
    mu: float
    gamma: float           # home advantage (log scale)
    rho: float
    half_life_years: float
    reg: float
    as_of: pd.Timestamp
    n_matches: int
    elo_equiv: dict[str, float] = field(default_factory=dict)

    def base_rate(self) -> float:
        """Neutral-venue base goals per team (= exp(mu))."""
        return math.exp(self.mu)

    def goal_rates(
        self, home: str, away: str, home_field: bool = False
    ) -> tuple[float, float]:
        """(lambda_home, lambda_away). home_field adds gamma to the home side."""
        ah = self.attack.get(home, 0.0)
        dh = self.defense.get(home, 0.0)
        aa = self.attack.get(away, 0.0)
        da = self.defense.get(away, 0.0)
        g = self.gamma if home_field else 0.0
        lam_h = math.exp(self.mu + ah - da + g)
        lam_a = math.exp(self.mu + aa - dh)
        return min(lam_h, LAMBDA_CLIP), min(lam_a, LAMBDA_CLIP)


def _prepare(
    df: pd.DataFrame, as_of: pd.Timestamp, half_life_years: float, max_age_years: float
):
    """Index teams and build the weighted observation arrays used by the fit."""
    hl = max(half_life_years, 1e-3)
    xi = math.log(2.0) / hl  # decay per year

    d = df[df["date"] <= as_of]
    if max_age_years:
        d = d[d["date"] >= as_of - pd.Timedelta(days=int(max_age_years * 365.25))]
    d = d.reset_index(drop=True)

    teams = sorted(set(d["home_team"]) | set(d["away_team"]))
    idx = {t: i for i, t in enumerate(teams)}
    T = len(teams)

    H = d["home_team"].map(idx).to_numpy()
    A = d["away_team"].map(idx).to_numpy()
    gh = d["home_score"].to_numpy(dtype=float)
    ga = d["away_score"].to_numpy(dtype=float)
    is_home = (~d["neutral"].to_numpy(dtype=bool)).astype(float)

    age_years = (as_of - d["date"]).dt.days.to_numpy() / 365.25
    w = np.exp(-xi * np.maximum(age_years, 0.0))

    return teams, idx, T, H, A, gh, ga, is_home, w, len(d)


def _unpack(params: np.ndarray, T: int):
    atk = params[:T]
    dfn = params[T : 2 * T]
    mu = params[2 * T]
    gamma = params[2 * T + 1]
    return atk, dfn, mu, gamma


def _objective_and_grad(params, T, H, A, gh, ga, is_home, w, reg):
    atk, dfn, mu, gamma = _unpack(params, T)

    eta_h = mu + atk[H] - dfn[A] + gamma * is_home
    eta_a = mu + atk[A] - dfn[H]
    lam_h = np.clip(np.exp(eta_h), 1e-9, LAMBDA_CLIP)
    lam_a = np.clip(np.exp(eta_a), 1e-9, LAMBDA_CLIP)

    # Weighted Poisson negative log-likelihood (drop constant log(y!)).
    nll = float(np.sum(w * (lam_h - gh * eta_h)) + np.sum(w * (lam_a - ga * eta_a)))
    nll += reg * float(np.sum(atk * atk) + np.sum(dfn * dfn))

    # Residuals: d(nll)/d(eta) = w * (lambda - y)
    r_h = w * (lam_h - gh)
    r_a = w * (lam_a - ga)

    g_atk = np.zeros(T)
    g_def = np.zeros(T)
    # attacker contributions (+r): home obs -> H, away obs -> A
    np.add.at(g_atk, H, r_h)
    np.add.at(g_atk, A, r_a)
    # defender contributions (-r): home obs defender = A, away obs defender = H
    np.add.at(g_def, A, -r_h)
    np.add.at(g_def, H, -r_a)
    g_atk += 2.0 * reg * atk
    g_def += 2.0 * reg * dfn

    g_mu = float(np.sum(r_h) + np.sum(r_a))
    g_gamma = float(np.sum(r_h * is_home))

    grad = np.concatenate([g_atk, g_def, [g_mu, g_gamma]])
    return nll, grad


def _fit_rho(model_lams_h, model_lams_a, gh, ga, w) -> float:
    """1-D profile MLE for the Dixon-Coles low-score correction rho."""
    gh_i = gh.astype(int)
    ga_i = ga.astype(int)
    # tau only differs from 1 when both teams scored <= 1; restrict for speed.
    mask = (gh_i <= 1) & (ga_i <= 1)
    if not mask.any():
        return 0.0
    lh = model_lams_h[mask]
    la = model_lams_a[mask]
    g1 = gh_i[mask]
    g2 = ga_i[mask]
    ww = w[mask]

    def neg_ll(rho: float) -> float:
        total = 0.0
        for i in range(len(g1)):
            t = _tau(int(g1[i]), int(g2[i]), float(lh[i]), float(la[i]), rho)
            total -= ww[i] * math.log(max(t, 1e-9))
        return total

    res = minimize_scalar(neg_ll, bounds=(-0.2, 0.2), method="bounded")
    return float(res.x)


def fit_model(
    df: pd.DataFrame,
    as_of: Optional[pd.Timestamp] = None,
    half_life_years: float = 2.5,
    reg: float = 0.08,
    max_age_years: float = 30.0,
) -> FittedModel:
    """Fit the time-weighted Dixon-Coles model on results up to `as_of`."""
    if as_of is None:
        as_of = pd.Timestamp(df["date"].max())
    as_of = pd.Timestamp(as_of)

    teams, idx, T, H, A, gh, ga, is_home, w, n = _prepare(
        df, as_of, half_life_years, max_age_years
    )

    x0 = np.zeros(2 * T + 2)
    x0[2 * T] = math.log(1.3)  # mu ~ typical goals/team
    x0[2 * T + 1] = 0.25       # gamma ~ home advantage prior

    res = minimize(
        _objective_and_grad,
        x0,
        args=(T, H, A, gh, ga, is_home, w, reg),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 500, "ftol": 1e-10, "gtol": 1e-7},
    )
    atk, dfn, mu, gamma = _unpack(res.x, T)

    # Profile rho at the fitted rates.
    eta_h = mu + atk[H] - dfn[A] + gamma * is_home
    eta_a = mu + atk[A] - dfn[H]
    lam_h = np.clip(np.exp(eta_h), 1e-9, LAMBDA_CLIP)
    lam_a = np.clip(np.exp(eta_a), 1e-9, LAMBDA_CLIP)
    rho = _fit_rho(lam_h, lam_a, gh, ga, w)

    attack = {t: float(atk[i]) for t, i in idx.items()}
    defense = {t: float(dfn[i]) for t, i in idx.items()}

    # Display Elo: overall strength = atk + def (a strong side both scores freely
    # AND concedes little, since `def` is defensive *strength*: larger lowers the
    # opponent's rate). Scaled to ~Elo spread (200 pts/unit), centred at 1900 so
    # existing UI ranges stay familiar.
    strength = {t: attack[t] + defense[t] for t in teams}
    s_vals = np.array(list(strength.values()))
    s_mean = float(s_vals.mean())
    elo_equiv = {t: 1900.0 + 200.0 * (strength[t] - s_mean) for t in teams}

    return FittedModel(
        teams=teams,
        attack=attack,
        defense=defense,
        mu=float(mu),
        gamma=float(gamma),
        rho=float(rho),
        half_life_years=half_life_years,
        reg=reg,
        as_of=as_of,
        n_matches=n,
        elo_equiv=elo_equiv,
    )


# ----------------------------------------------------------------- persistence
def model_to_dict(m: FittedModel) -> dict:
    return {
        "teams": m.teams,
        "attack": m.attack,
        "defense": m.defense,
        "mu": m.mu,
        "gamma": m.gamma,
        "rho": m.rho,
        "half_life_years": m.half_life_years,
        "reg": m.reg,
        "as_of": pd.Timestamp(m.as_of).isoformat(),
        "n_matches": m.n_matches,
        "elo_equiv": m.elo_equiv,
    }


def model_from_dict(d: dict) -> FittedModel:
    return FittedModel(
        teams=list(d["teams"]),
        attack=dict(d["attack"]),
        defense=dict(d["defense"]),
        mu=float(d["mu"]),
        gamma=float(d["gamma"]),
        rho=float(d["rho"]),
        half_life_years=float(d["half_life_years"]),
        reg=float(d["reg"]),
        as_of=pd.Timestamp(d["as_of"]),
        n_matches=int(d["n_matches"]),
        elo_equiv=dict(d.get("elo_equiv", {})),
    )


def save_model(m: FittedModel, path: str = "fitted_ratings.json") -> None:
    import json
    with open(path, "w") as fh:
        json.dump(model_to_dict(m), fh)


def load_model(path: str = "fitted_ratings.json") -> Optional[FittedModel]:
    import json
    import os
    if not os.path.exists(path):
        return None
    try:
        with open(path) as fh:
            return model_from_dict(json.load(fh))
    except Exception:
        return None
