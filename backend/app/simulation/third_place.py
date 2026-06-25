"""
Select the 8 best 3rd-placed teams from 12 groups and assign them to R32 slots.

The FIFA 2026 bracket encodes which groups are eligible for each 3rd-place R32 slot
as strings like "3A/B/C/D/F". We use those strings to define the seeding table.
"""

import numpy as np

# Eligible group letters for each of the 8 R32 slots that receive 3rd-place teams.
# Derived directly from the OpenFootball worldcup.json bracket notation.
# Key = R32 match number (73-88), value = set of eligible group letters.
THIRD_PLACE_SLOTS: dict[int, frozenset[str]] = {
    74: frozenset("ABCDF"),
    77: frozenset("CDFGH"),
    79: frozenset("CEFHI"),
    80: frozenset("EHIJK"),
    81: frozenset("BEFIJ"),
    82: frozenset("AEHIJ"),
    85: frozenset("EFGIJ"),
    87: frozenset("DEIJL"),
}

# Ordered list of slot match numbers (for deterministic assignment)
_SLOT_ORDER = sorted(THIRD_PLACE_SLOTS.keys())

_GROUP_LETTERS = "ABCDEFGHIJKL"

# Official FIFA 2026 third-place allocation (Regulations Annexe C): for each of the
# 495 combinations of qualifying groups, the fixed {r32_match_number: group index}
# assignment. Replaces an arbitrary perfect matching so projected R32 opponents match
# the real bracket (e.g. 1D = USA reliably draws the same third-place team the actual
# table dictates, instead of being shuffled by the matcher). O(1) lookup per sim.
from app.simulation.third_place_allocation import (
    OFFICIAL_THIRD_PLACE_ASSIGNMENT as _THIRD_PLACE_ASSIGNMENT,
)


def select_third_place_qualifiers(
    ranks: np.ndarray,       # (N, 12, 4) — local team idx by rank
    pts:   np.ndarray,       # (N, 12, 4)
    gd:    np.ndarray,       # (N, 12, 4)
    gf:    np.ndarray,       # (N, 12, 4)
    global_team_ids: np.ndarray,  # (12, 4) — global team index per group/local
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns:
      third_global (N, 12) — global team index of each group's 3rd-place finisher
      qualifiers   (N, 8)  — global team indices of the 8 best 3rd-placers,
                             in slot order matching _SLOT_ORDER
    """
    N = ranks.shape[0]
    G = 12

    # Extract 3rd-place finisher from each group (local rank index 2)
    third_local = ranks[:, :, 2]                     # (N, 12)
    idx_n = np.arange(N)[:, None]                    # broadcast helper
    idx_g = np.arange(G)[None, :]

    third_pts = pts[idx_n, idx_g, third_local]       # (N, 12)
    third_gd  = gd [idx_n, idx_g, third_local]       # (N, 12)
    third_gf  = gf [idx_n, idx_g, third_local]       # (N, 12)

    # Global team index of each group's 3rd-place team
    third_global = global_team_ids[idx_g, third_local]  # (N, 12)

    # Rank the 12 third-place teams: best 8 qualify
    noise = np.random.rand(N, G) * 1e-4
    score = (
        third_pts.astype(np.float64) * 1e6
        + third_gd.astype(np.float64) * 1000
        + third_gf.astype(np.float64)
        + noise
    )
    # Sort groups by score descending: (N, 12) indices
    grp_rank = np.argsort(-score, axis=1)  # (N, 12)
    qualifying_grp_indices = grp_rank[:, :8]  # (N, 8) — group indices (0-11)

    # Assign each qualifier to its bracket slot via the precomputed perfect matching.
    qualifiers = np.zeros((N, 8), dtype=np.int32)
    slot_pos = {slot: i for i, slot in enumerate(_SLOT_ORDER)}

    for n in range(N):
        qual = frozenset(int(g) for g in qualifying_grp_indices[n])  # 8 distinct groups
        assignment = _THIRD_PLACE_ASSIGNMENT.get(qual)  # {slot: group_idx}
        if assignment is None:
            # No perfect matching exists for this combo (never happens for the real
            # eligibility table — all 495 combos match). Degrade to slot order.
            for s_i in range(8):
                qualifiers[n, s_i] = third_global[n, qualifying_grp_indices[n, s_i]]
            continue
        for slot, gi in assignment.items():
            qualifiers[n, slot_pos[slot]] = third_global[n, gi]

    return third_global, qualifiers


def third_place_qualification_odds(
    qualifies: np.ndarray,  # (N,) bool — does this team qualify as 3rd?
) -> dict[str, float]:
    N = len(qualifies)
    return {"p_qualify_as_3rd": float(qualifies.sum() / N)}
