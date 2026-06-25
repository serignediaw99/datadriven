"""
Per-player goal and assist accumulation across simulations.

Strategy:
  - For each unplayed match, team expected goals = λ (from Poisson model).
  - Goals are distributed among players using each player's share of their
    team's goals so far. New players with 0 goals get a small baseline share.
  - Sample each player's goals in each sim from Binomial(total_team_goals, player_share).

Output:
  goals_by_player (N, P) — simulated total goals per player after all matches.
  assists_by_player (N, P) — same for assists.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class PlayerEntry:
    name: str
    team: str
    current_goals: int = 0
    current_assists: int = 0
    team_global_idx: int = -1


def build_player_entries(
    scorer_tally: dict[str, int],      # from openfootball goals1/goals2
    assist_tally: dict[str, int],      # from fbref (may be empty)
    team_of_player: dict[str, str],    # player → team name
    team_name_to_idx: dict[str, int],
    top_n: int = 40,
) -> list[PlayerEntry]:
    """
    Return top_n players by current goals as PlayerEntry objects.
    Includes players with current_goals > 0 plus leading assist providers.
    """
    all_names = set(scorer_tally) | set(assist_tally) | set(team_of_player)
    entries: list[PlayerEntry] = []
    for name in all_names:
        team = team_of_player.get(name, "")
        if not team:
            continue
        entries.append(
            PlayerEntry(
                name=name,
                team=team,
                current_goals=scorer_tally.get(name, 0),
                current_assists=assist_tally.get(name, 0),
                team_global_idx=team_name_to_idx.get(team, -1),
            )
        )
    # Keep the leading scorers AND the leading assist providers — taking the top
    # purely by goals would drop assist-only players (0 goals) from the assists
    # ladder entirely. Union the two leaderboards, de-duplicated.
    by_goals   = sorted(entries, key=lambda e: (-e.current_goals, -e.current_assists))
    by_assists = sorted(entries, key=lambda e: (-e.current_assists, -e.current_goals))
    selected: list[PlayerEntry] = []
    seen: set[str] = set()
    for e in by_goals[:top_n] + by_assists[:top_n]:
        if e.name not in seen:
            seen.add(e.name)
            selected.append(e)
    return selected


def simulate_player_goals(
    players: list[PlayerEntry],
    team_remaining_goals: dict[int, np.ndarray],  # team_global_idx → (N,) remaining goals
    team_total_scored: dict[int, int],              # already-played goals
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (goals_arr, assists_arr) each shape (N, len(players)).

    goals_arr[n, p] = total WC goals for player p in sim n (current + future).
    """
    if not players:
        return np.zeros((1, 0), dtype=np.int32), np.zeros((1, 0), dtype=np.int32)

    # Infer N from the first team's remaining goals array
    N = next(iter(team_remaining_goals.values())).shape[0] if team_remaining_goals else 1
    P = len(players)

    goals_arr   = np.zeros((N, P), dtype=np.int32)
    assists_arr = np.zeros((N, P), dtype=np.int32)

    # Group players by team
    team_players: dict[int, list[tuple[int, PlayerEntry]]] = {}
    for p_idx, player in enumerate(players):
        ti = player.team_global_idx
        team_players.setdefault(ti, []).append((p_idx, player))

    for ti, p_list in team_players.items():
        if ti < 0:
            continue

        # Current tournament goals by this team's players
        team_current = team_total_scored.get(ti, 0)

        # Build share vector for goal distribution
        raw_goals = np.array([e.current_goals for _, e in p_list], dtype=np.float64)
        # Give a small baseline to all tracked players
        baseline = max(0.2, raw_goals.mean() * 0.1) if raw_goals.sum() > 0 else 0.2
        shares = raw_goals + baseline
        shares /= shares.sum()  # normalise

        # Simulated remaining goals for this team across N sims
        rem_goals = team_remaining_goals.get(ti, np.zeros(N, dtype=np.int32))

        # Distribute future team goals among players.
        # Sample each player's goals from Poisson(rem_goals[n] * share[j]) — a
        # standard approximation to Multinomial(rem_goals, shares) that is fully
        # vectorised across both sims and players.
        expected = rem_goals[:, np.newaxis] * shares[np.newaxis, :]  # (N, K)
        future_goals = np.random.poisson(expected).astype(np.int32)

        # Add current goals
        current_arr = np.array([e.current_goals for _, e in p_list], dtype=np.int32)
        total_goals = future_goals + current_arr[np.newaxis, :]  # (N, len(p_list))

        # Write back
        for local_i, (p_idx, _) in enumerate(p_list):
            goals_arr[:, p_idx] = total_goals[:, local_i]

        # Simple assist estimate: ~0.6 assists per goal for assisted goals
        assist_share_arr = np.array([e.current_assists for _, e in p_list], dtype=np.float64)
        assist_base = max(0.1, assist_share_arr.mean() * 0.1) if assist_share_arr.sum() > 0 else 0.1
        a_shares = assist_share_arr + assist_base
        a_shares /= a_shares.sum()
        assisted_goals = (rem_goals * 0.8)
        a_expected = assisted_goals[:, np.newaxis] * a_shares[np.newaxis, :]  # (N, K)
        future_assists = np.random.poisson(a_expected).astype(np.int32)

        current_ast = np.array([e.current_assists for _, e in p_list], dtype=np.int32)
        total_assists = future_assists + current_ast[np.newaxis, :]

        for local_i, (p_idx, _) in enumerate(p_list):
            assists_arr[:, p_idx] = total_assists[:, local_i]

    return goals_arr, assists_arr
