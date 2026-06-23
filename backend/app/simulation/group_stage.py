"""
Vectorized group-stage simulation for all 12 groups simultaneously.

Input:
  goals1 (N, 72), goals2 (N, 72)  — goals in each group-stage match for N sims.
  group_meta: GroupMeta per group

Output:
  ranks (N, 12, 4)  — local team index ranked 1st–4th in each sim
  pts   (N, 12, 4)
  gd    (N, 12, 4)
  gf    (N, 12, 4)
"""

from dataclasses import dataclass, field

import numpy as np

# 6 matches in a group of 4. Ordered pairs of team indices (t1, t2) within group.
GROUP_MATCHUPS: list[tuple[int, int]] = [
    (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3),
]


@dataclass
class GroupMeta:
    name: str               # e.g. "Group A"
    teams: list[str]        # 4 team names in local order 0..3
    match_indices: list[int]  # 6 indices into the 72-match global array


def compute_group_standings(
    goals1: np.ndarray,  # (N, 72)
    goals2: np.ndarray,  # (N, 72)
    groups: list[GroupMeta],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (ranks, pts, gd, gf) each shape (N, 12, 4).

    ranks[n, g, 0] = local team index of group-g winner in sim n.
    ranks[n, g, 3] = local team index of group-g last place in sim n.
    """
    N = goals1.shape[0]
    G = len(groups)  # 12

    pts = np.zeros((N, G, 4), dtype=np.int32)
    gd  = np.zeros((N, G, 4), dtype=np.int32)
    gf  = np.zeros((N, G, 4), dtype=np.int32)

    for g_idx, grp in enumerate(groups):
        for m_local, (t1, t2) in enumerate(GROUP_MATCHUPS):
            mi = grp.match_indices[m_local]
            g1 = goals1[:, mi]  # (N,)
            g2 = goals2[:, mi]  # (N,)

            win1 = (g1 > g2).astype(np.int32)
            win2 = (g2 > g1).astype(np.int32)
            drw  = (g1 == g2).astype(np.int32)

            pts[:, g_idx, t1] += 3 * win1 + drw
            pts[:, g_idx, t2] += 3 * win2 + drw
            gd[:, g_idx, t1]  += g1 - g2
            gd[:, g_idx, t2]  += g2 - g1
            gf[:, g_idx, t1]  += g1
            gf[:, g_idx, t2]  += g2

    # ── Pairwise H2H pts matrix ────────────────────────────────────────────────
    # h2h[n, g, i, j] = pts team i earned in their direct match against team j.
    # Used as the tiebreaker when two or more teams share the same overall pts.
    h2h = np.zeros((N, G, 4, 4), dtype=np.float64)
    for g_idx, grp in enumerate(groups):
        for m_local, (t1, t2) in enumerate(GROUP_MATCHUPS):
            mi = grp.match_indices[m_local]
            g1 = goals1[:, mi].astype(np.float64)
            g2 = goals2[:, mi].astype(np.float64)
            h2h[:, g_idx, t1, t2] += 3.0 * (g1 > g2) + (g1 == g2)
            h2h[:, g_idx, t2, t1] += 3.0 * (g2 > g1) + (g1 == g2)

    # For each team i, sum the net H2H edge only against opponents tied on pts.
    # tied_mask[n,g,i,j] = 1 if pts[i]==pts[j] in that sim (excludes self).
    pts_f = pts.astype(np.float64)
    tied = (pts_f[:, :, :, np.newaxis] == pts_f[:, :, np.newaxis, :])   # (N,G,4,4)
    np.einsum('ngii->ngi', tied.view(np.uint8)).fill(0)  # zero the diagonal
    h2h_edge  = h2h - h2h.transpose(0, 1, 3, 2)           # net pts: +3 win, 0 draw, -3 loss
    h2h_bonus = (h2h_edge * tied).sum(axis=3)              # (N, G, 4)

    # Combined ranking key (descending).  Weight hierarchy ensures FIFA order:
    #   overall pts > H2H pts (among tied) > overall GD > overall GF > lots
    noise = np.random.rand(N, G, 4) * 1e-4
    combined = (
        pts_f * 1e9
        + h2h_bonus * 1e6          # only non-zero when pts are tied
        + gd.astype(np.float64) * 1e3
        + gf.astype(np.float64)
        + noise
    )
    ranks = np.argsort(-combined, axis=2)  # (N, G, 4) — local team indices

    return ranks, pts, gd, gf
