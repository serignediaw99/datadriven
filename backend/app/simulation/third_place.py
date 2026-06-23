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

    # Assign each qualifier to its bracket slot using eligible groups
    group_letters = list("ABCDEFGHIJKL")  # index 0 = A, ..., 11 = L

    qualifiers = np.zeros((N, 8), dtype=np.int32)

    for n in range(N):
        qual_groups = set(qualifying_grp_indices[n])  # group indices 0-11
        # Map group index → letter
        qual_letters = {group_letters[gi]: gi for gi in qual_groups}

        remaining_groups = dict(qual_letters)  # letter → group_idx; to be assigned
        remaining_slots = list(_SLOT_ORDER)     # slot match numbers to fill

        assignment: dict[int, int] = {}  # slot → group_idx

        # Greedy: for each slot, assign the first eligible qualifying group
        for slot in remaining_slots:
            eligible = THIRD_PLACE_SLOTS[slot]
            for letter, gi in list(remaining_groups.items()):
                if letter in eligible:
                    assignment[slot] = gi
                    del remaining_groups[letter]
                    break

        # Fill qualifiers in slot order
        for s_i, slot in enumerate(_SLOT_ORDER):
            gi = assignment.get(slot, qualifying_grp_indices[n, s_i])
            qualifiers[n, s_i] = third_global[n, gi]

    return third_global, qualifiers


def third_place_qualification_odds(
    qualifies: np.ndarray,  # (N,) bool — does this team qualify as 3rd?
) -> dict[str, float]:
    N = len(qualifies)
    return {"p_qualify_as_3rd": float(qualifies.sum() / N)}
