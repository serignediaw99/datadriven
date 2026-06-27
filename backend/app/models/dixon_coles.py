"""
Dixon-Coles correction for the bivariate Poisson model.

Applied to the pre-match scoreline probability matrix only.
The Monte Carlo engine uses plain Poisson for speed.

Reference: Dixon & Coles (1997) — modelling association football scores.
"""

import math
import numpy as np

RHO = -0.130  # empirical correction factor for football low scores


def _tau(g1: int, g2: int, lam1: float, lam2: float, rho: float = RHO) -> float:
    """Dixon-Coles adjustment for low-scoring outcomes."""
    if g1 == 0 and g2 == 0:
        return 1 - lam1 * lam2 * rho
    if g1 == 1 and g2 == 0:
        return 1 + lam2 * rho
    if g1 == 0 and g2 == 1:
        return 1 + lam1 * rho
    if g1 == 1 and g2 == 1:
        return 1 - rho
    return 1.0


def scoreline_matrix(
    lam1: float, lam2: float, max_goals: int = 8, rho: float = RHO
) -> np.ndarray:
    """
    Return a (max_goals+1, max_goals+1) matrix P[g1, g2] = P(score is g1-g2).

    Rows = goals by team1, columns = goals by team2.
    ``rho`` is the Dixon-Coles low-score correction; pass the fitted model's rho
    so the displayed scoreline grid matches the strength model. Sum ≈ 1.0.
    """
    mat = np.zeros((max_goals + 1, max_goals + 1))
    for g1 in range(max_goals + 1):
        for g2 in range(max_goals + 1):
            p = (
                math.exp(-lam1) * lam1**g1 / math.factorial(g1)
                * math.exp(-lam2) * lam2**g2 / math.factorial(g2)
                * _tau(g1, g2, lam1, lam2, rho)
            )
            mat[g1, g2] = max(p, 0.0)
    # Renormalise after tau adjustments
    total = mat.sum()
    if total > 0:
        mat /= total
    return mat


def derived_stats(mat: np.ndarray) -> dict[str, float]:
    """Compute summary statistics from the scoreline probability matrix."""
    n = mat.shape[0]
    goals = np.arange(n)

    # mat[g1, g2]: rows = goals by team1, cols = goals by team2.
    # Lower triangle (row > col → g1 > g2) = team1 wins.
    # Upper triangle (col > row → g2 > g1) = team2 wins.
    p_home = float(np.tril(mat, k=-1).sum())  # g1 > g2
    p_draw = float(np.trace(mat))
    p_away = float(np.triu(mat, k=1).sum())   # g2 > g1

    # xG proxy: expected goals from the distribution
    xg1 = float((mat.sum(axis=1) * goals).sum())
    xg2 = float((mat.sum(axis=0) * goals).sum())

    # Over 2.5
    over_25 = float(1 - sum(mat[g1, g2] for g1 in range(n) for g2 in range(n) if g1 + g2 <= 2))

    # Both teams score
    btts = float(1 - mat[:, 0].sum() - mat[0, :].sum() + mat[0, 0])

    # Clean sheet probability per team
    cs1 = float(mat[:, 0].sum())   # team2 scores 0
    cs2 = float(mat[0, :].sum())   # team1 scores 0

    # Most likely scoreline
    idx = np.unravel_index(mat.argmax(), mat.shape)
    most_likely = (int(idx[0]), int(idx[1]), float(mat[idx]))

    return {
        "p_home_win": p_home,
        "p_draw": p_draw,
        "p_away_win": p_away,
        "xg_home": xg1,
        "xg_away": xg2,
        "p_over_25": over_25,
        "p_btts": btts,
        "p_clean_sheet_home": cs1,
        "p_clean_sheet_away": cs2,
        "most_likely_score": f"{most_likely[0]}-{most_likely[1]}",
        "most_likely_score_prob": most_likely[2],
    }
