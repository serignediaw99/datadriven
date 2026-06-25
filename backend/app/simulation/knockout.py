"""
Vectorized knockout-bracket simulation (R32 -> Final).

The bracket is fixed: 16 R32 matches, 8 R16 matches, 4 QF, 2 SF, 1 Final.
Teams are identified by their global index (0-47).

Ties in 90 mins are resolved by a 50/50 coin flip (models extra-time + pens).
"""

import numpy as np

# R32 bracket slot descriptors. Source: openfootball worldcup.json.
R32_STRUCTURE: list[tuple[str, str]] = [
    ("2:A", "2:B"),        # match 73
    ("1:E", "3:0"),        # match 74  (1:E = Germany if they win Group E)
    ("1:F", "2:C"),        # match 75
    ("1:C", "2:F"),        # match 76
    ("1:I", "3:1"),        # match 77
    ("2:E", "2:I"),        # match 78
    ("1:A", "3:2"),        # match 79  (1:A = Mexico if they win Group A)
    ("1:L", "3:3"),        # match 80
    ("1:D", "3:4"),        # match 81  (1:D = USA if they win Group D)
    ("1:G", "3:5"),        # match 82
    ("2:K", "2:L"),        # match 83
    ("1:H", "2:J"),        # match 84
    ("1:B", "3:6"),        # match 85
    ("1:J", "2:H"),        # match 86
    ("1:K", "3:7"),        # match 87
    ("2:D", "2:G"),        # match 88
]

R16_BRACKET = [
    (1, 4),   # W74 vs W77  (match 89)
    (0, 2),   # W73 vs W75  (match 90)
    (3, 5),   # W76 vs W78  (match 91)
    (6, 7),   # W79 vs W80  (match 92)
    (10, 11), # W83 vs W84  (match 93)
    (8, 9),   # W81 vs W82  (match 94)
    (13, 15), # W86 vs W88  (match 95)
    (12, 14), # W85 vs W87  (match 96)
]
QF_BRACKET = [
    (0, 1),  # W89 vs W90  (match 97)
    (4, 5),  # W93 vs W94  (match 98)
    (2, 3),  # W91 vs W92  (match 99)
    (6, 7),  # W95 vs W96  (match 100)
]
SF_BRACKET = [
    (0, 1),  # W97 vs W98  (match 101)
    (2, 3),  # W99 vs W100 (match 102)
]
# Final: match 104

# Real match number -> (round_name, bracket_position)
KO_MATCH_TO_BRACKET: dict[int, tuple[str, int]] = {
    **{73 + i: ("R32", i) for i in range(16)},
    **{89 + i: ("R16", i) for i in range(8)},
    **{97 + i: ("QF",  i) for i in range(4)},
    101: ("SF", 0),
    102: ("SF", 1),
    104: ("Final", 0),
}


def _resolve_slot(
    desc: str,
    ranks: np.ndarray,
    global_ids: np.ndarray,
    third_qualifiers: np.ndarray,
    team_name_to_idx: dict[str, int],
) -> np.ndarray:
    N = ranks.shape[0]
    kind, val = desc.split(":", 1)
    if kind == "team":
        idx = team_name_to_idx[val]
        return np.full(N, idx, dtype=np.int32)
    if kind == "1":
        g = ord(val) - ord("A")
        return global_ids[g, ranks[:, g, 0]]
    if kind == "2":
        g = ord(val) - ord("A")
        return global_ids[g, ranks[:, g, 1]]
    if kind == "3":
        return third_qualifiers[:, int(val)]
    raise ValueError(f"Unknown slot: {desc!r}")


def simulate_knockout(
    ranks: np.ndarray,
    global_team_ids: np.ndarray,
    third_qualifiers: np.ndarray,
    lam: dict[int, tuple[float, float]],
    team_name_to_idx: dict[str, int],
    base_rate: float = 1.15,
    fixed_ko: dict[str, dict[int, int]] | None = None,
    home_adv: float = 0.0,
    ko_host: dict[str, dict[int, int]] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run R32->Final for all N sims.

    fixed_ko: {round_name: {bracket_pos: winner_global_idx}} for played matches.

    Returns:
      reach    (N, 48, 6) bool   -- team t reaches round r in sim n
      ko_goals (N, 48) int32     -- goals scored in KO rounds per team per sim
      ko_opp   (N, 48, 6) int8   -- opponent global idx per team per round (-1=none)
    """
    N = ranks.shape[0]
    T = 48
    reach    = np.zeros((N, T, 6), dtype=bool)
    ko_goals = np.zeros((N, T), dtype=np.int32)
    ko_opp   = np.full((N, T, 6), -1, dtype=np.int8)
    row_idx  = np.arange(N)

    if fixed_ko is None:
        fixed_ko = {}
    if ko_host is None:
        ko_host = {}

    # Pre-build vectorized alpha/beta arrays indexed by team global idx
    all_alpha = np.zeros(T, dtype=np.float64)
    all_beta  = np.zeros(T, dtype=np.float64)
    for ti, (a, b) in lam.items():
        if 0 <= ti < T:
            all_alpha[ti] = a
            all_beta[ti]  = b

    def _play_round(
        participants: np.ndarray,
        bracket: list[tuple[int, int]],
        round_idx: int,
        round_name: str,
    ) -> np.ndarray:
        M = len(bracket)
        winners = np.zeros((N, M), dtype=np.int32)
        fixed_round = fixed_ko.get(round_name, {})
        host_round = ko_host.get(round_name, {})

        for i, (a, b) in enumerate(bracket):
            t1 = participants[:, a]
            t2 = participants[:, b]

            # Record opponents for path analysis
            ko_opp[row_idx, t1, round_idx] = t2.astype(np.int8)
            ko_opp[row_idx, t2, round_idx] = t1.astype(np.int8)

            # Use fixed winner for already-played matches
            if i in fixed_round:
                winners[:, i] = fixed_round[i]
                continue

            # Host advantage: if this venue is in a host country, the host team
            # (when present) gets +home_adv on its goal rate.
            host_idx = host_round.get(i, -1)
            if host_idx >= 0 and home_adv:
                h1 = np.where(t1 == host_idx, home_adv, 0.0)
                h2 = np.where(t2 == host_idx, home_adv, 0.0)
            else:
                h1 = h2 = 0.0

            # Vectorized lambda via fancy indexing
            lam1 = base_rate * np.exp(all_alpha[t1] - all_beta[t2] + h1)
            lam2 = base_rate * np.exp(all_alpha[t2] - all_beta[t1] + h2)
            g1 = np.random.poisson(lam1).astype(np.int32)
            g2 = np.random.poisson(lam2).astype(np.int32)
            wins_t1 = (g1 > g2) | ((g1 == g2) & (np.random.rand(N) < 0.5))
            winners[:, i] = np.where(wins_t1, t1, t2)

            np.add.at(ko_goals, (row_idx, t1), g1)
            np.add.at(ko_goals, (row_idx, t2), g2)

        return winners

    # Build R32 participants (N, 32)
    r32 = np.zeros((N, 32), dtype=np.int32)
    for mi, (d1, d2) in enumerate(R32_STRUCTURE):
        r32[:, 2*mi]   = _resolve_slot(d1, ranks, global_team_ids, third_qualifiers, team_name_to_idx)
        r32[:, 2*mi+1] = _resolve_slot(d2, ranks, global_team_ids, third_qualifiers, team_name_to_idx)

    # Mark R32 participants (reach round 0)
    for t in range(32):
        reach[row_idx, r32[:, t], 0] = True

    r32_bracket = [(2*i, 2*i+1) for i in range(16)]
    r16_teams = _play_round(r32, r32_bracket, round_idx=0, round_name="R32")
    for t_col in range(16):
        reach[row_idx, r16_teams[:, t_col], 1] = True

    qf_teams = _play_round(r16_teams, R16_BRACKET, round_idx=1, round_name="R16")
    for t_col in range(8):
        reach[row_idx, qf_teams[:, t_col], 2] = True

    sf_teams = _play_round(qf_teams, QF_BRACKET, round_idx=2, round_name="QF")
    for t_col in range(4):
        reach[row_idx, sf_teams[:, t_col], 3] = True

    finalists = _play_round(sf_teams, [(0, 1), (2, 3)], round_idx=3, round_name="SF")
    for t_col in range(2):
        reach[row_idx, finalists[:, t_col], 4] = True

    winner = _play_round(finalists, [(0, 1)], round_idx=4, round_name="Final")
    reach[row_idx, winner[:, 0], 5] = True

    return reach, ko_goals, ko_opp
