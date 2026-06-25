"""
Convert Elo ratings → per-match Poisson λ parameters.

Model:
  λ_i_vs_j = BASE_RATE * exp(α_i - β_j)

where α (attack) and β (defense) are derived from Elo ratings
relative to the average of the 48 teams.

Calibrated for neutral-venue World Cup matches (~1.15 goals/team).
"""

import math
from dataclasses import dataclass

BASE_RATE = 1.15  # avg goals per team per WC match (neutral venue)
HOME_ADV = 0.0    # host advantage (log scale); set from the fitted model's gamma
ATTACK_SCALE = 0.40   # how strongly Elo drives attack
DEFENSE_SCALE = 0.30  # how strongly Elo drives defense
ELO_UNIT = 200.0      # Elo points per unit


@dataclass(frozen=True)
class TeamParams:
    name: str
    elo: float
    alpha: float  # attack parameter (log scale)
    beta: float   # defense parameter (log scale)


def build_team_params(elo_ratings: dict[str, float]) -> dict[str, TeamParams]:
    """
    Given {team_name: elo}, return {team_name: TeamParams}.
    """
    if not elo_ratings:
        return {}
    avg_elo = sum(elo_ratings.values()) / len(elo_ratings)
    params: dict[str, TeamParams] = {}
    for name, elo in elo_ratings.items():
        delta = (elo - avg_elo) / ELO_UNIT
        params[name] = TeamParams(
            name=name,
            elo=elo,
            alpha=ATTACK_SCALE * delta,
            beta=DEFENSE_SCALE * delta,
        )
    return params


def build_team_params_from_model(
    model, team_names: list[str] | None = None
) -> dict[str, TeamParams]:
    """
    Build TeamParams from a fitted Dixon-Coles model (app.models.fit_dixon_coles).

    Also updates the module-level BASE_RATE and HOME_ADV so the simulation engine
    (which reads them via the ratings module) uses the fitted neutral base rate
    and host advantage. Teams absent from the fit are skipped — the caller can
    fall back to the Elo heuristic for those.
    """
    global BASE_RATE, HOME_ADV
    BASE_RATE = model.base_rate()
    HOME_ADV = float(model.gamma)
    names = team_names if team_names is not None else list(model.teams)
    params: dict[str, TeamParams] = {}
    for name in names:
        if name in model.attack:
            params[name] = TeamParams(
                name=name,
                elo=float(model.elo_equiv.get(name, 1900.0)),
                alpha=float(model.attack[name]),
                beta=float(model.defense[name]),
            )
    return params


def expected_goals(
    attacker: TeamParams,
    defender: TeamParams,
) -> float:
    """λ for attacker scoring against defender in a neutral-venue match."""
    return BASE_RATE * math.exp(attacker.alpha - defender.beta)


def match_lambdas(
    team1: TeamParams,
    team2: TeamParams,
) -> tuple[float, float]:
    """Return (λ1, λ2) for a neutral-venue match."""
    return expected_goals(team1, team2), expected_goals(team2, team1)


def win_probability(lam1: float, lam2: float, max_goals: int = 10) -> tuple[float, float, float]:
    """
    Compute P(team1 wins), P(draw), P(team2 wins) from Poisson parameters.
    Uses exact summation over goal grid up to max_goals.
    """
    from scipy.stats import poisson  # type: ignore

    p1 = poisson(lam1)
    p2 = poisson(lam2)
    p_win1 = p_draw = p_win2 = 0.0
    for g1 in range(max_goals + 1):
        for g2 in range(max_goals + 1):
            p = p1.pmf(g1) * p2.pmf(g2)
            if g1 > g2:
                p_win1 += p
            elif g1 == g2:
                p_draw += p
            else:
                p_win2 += p
    return p_win1, p_draw, p_win2
