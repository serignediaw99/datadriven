"""
Main simulation engine: runs N full-tournament Monte Carlo simulations.

All N sims are run in a single vectorized NumPy pass for performance.
Target: 50,000 sims in < 15 seconds on a MacBook M-series.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.data.openfootball import WCMatch
from app.data.metadata import host_playing_at_home, VENUE_COUNTRY, HOSTS_2026
from app.models import ratings
from app.models.ratings import TeamParams
from app.simulation.group_stage import GroupMeta, compute_group_standings, GROUP_MATCHUPS
from app.simulation.third_place import select_third_place_qualifiers
from app.simulation.knockout import simulate_knockout, KO_MATCH_TO_BRACKET
from app.simulation.players import PlayerEntry, simulate_player_goals
from app.simulation import aggregator


GROUP_LETTERS = list("ABCDEFGHIJKL")
GROUP_STAGE_ROUNDS = {"Matchday " + str(i) for i in range(1, 18)}


@dataclass
class SimulationResult:
    # Group stage
    group_odds: list[dict]
    third_place_odds: list[dict]

    # Knockout
    knockout_odds: list[dict]

    # Awards
    golden_boot: list[dict]
    top_assists: list[dict]

    # Meta
    n_simulations: int
    elapsed_seconds: float
    timestamp: float = field(default_factory=time.time)

    # Raw arrays for on-demand path analysis
    team_names: list[str] = field(default_factory=list)
    reach: Optional[np.ndarray] = None   # (N, 48, 6) bool
    ko_opp: Optional[np.ndarray] = None  # (N, 48, 6) int8


def run(
    matches: list[WCMatch],
    team_params: dict[str, TeamParams],
    players: list[PlayerEntry],
    n: int = 50_000,
    match_lambda_overrides: Optional[dict[int, tuple[float, float]]] = None,
    inplay: Optional[dict[int, tuple[int, int, float]]] = None,
) -> SimulationResult:
    # match_lambda_overrides: {match.num: (lambda_team1, lambda_team2)} — bookmaker
    # h2h-derived goal rates that replace the model's for specific upcoming group
    # fixtures (in data orientation, i.e. for m.team1 / m.team2).
    # inplay: {match.num: (current_team1_goals, current_team2_goals, fraction_remaining)}
    # for live group fixtures — the current score is fixed and only the remaining
    # fraction of the match is sampled (fraction 0.0 = treat as final). Data orientation.
    t0 = time.perf_counter()

    # --- Build global team index ---
    group_teams: dict[str, list[str]] = {}
    for m in matches:
        if m.group:
            group_teams.setdefault(m.group, [])
            for t in (m.team1, m.team2):
                if t not in group_teams[m.group]:
                    group_teams[m.group].append(t)
    for g in sorted(group_teams):
        group_teams[g].sort()

    # 48 team names in deterministic order (group A first, then B, …)
    team_names: list[str] = []
    for g in sorted(group_teams):
        team_names.extend(group_teams[g])

    team_to_idx: dict[str, int] = {t: i for i, t in enumerate(team_names)}

    # (12, 4) array of global team indices per group/local position
    group_order = sorted(group_teams.keys())  # Groups A-L
    global_team_ids = np.array(
        [[team_to_idx[t] for t in group_teams[g]] for g in group_order],
        dtype=np.int32,
    )  # (12, 4)

    # --- Identify group-stage matches and build GroupMeta ---
    group_matches: dict[str, list[WCMatch]] = {g: [] for g in group_order}
    for m in matches:
        if m.group:
            group_matches[m.group].append(m)

    # Assign match indices 0-71 in canonical group-matchup order.
    # Also track whether score needs flipping (data team1 ≠ canonical t1).
    groups: list[GroupMeta] = []
    match_index_map: dict[int, int] = {}  # match.num → flat index 0..71
    match_flip_map: dict[int, bool] = {}  # match.num → True if scores are swapped

    flat_idx = 0
    for g in group_order:
        local_teams = group_teams[g]  # 4 teams in local order 0..3
        grp_matches_sorted = sorted(group_matches[g], key=lambda m: m.num)
        match_idx_list: list[int] = []
        for (li, lj) in GROUP_MATCHUPS:
            t1_name = local_teams[li]
            t2_name = local_teams[lj]
            found = next(
                (m for m in grp_matches_sorted
                 if set([m.team1, m.team2]) == {t1_name, t2_name}),
                None,
            )
            if found:
                match_index_map[found.num] = flat_idx
                # Flip if the data match lists t2 first (data.team1 == canonical t2)
                match_flip_map[found.num] = (found.team1 == t2_name)
            match_idx_list.append(flat_idx)
            flat_idx += 1
        groups.append(GroupMeta(name=g, teams=local_teams, match_indices=match_idx_list))

    # --- Build goals arrays (N, 72) ---
    goals1 = np.zeros((n, 72), dtype=np.int32)
    goals2 = np.zeros((n, 72), dtype=np.int32)

    # Fill in already-played matches (constant across all sims).
    # Respect the canonical team order stored in match_flip_map.
    for m in matches:
        if m.group and m.is_played and m.num in match_index_map:
            fi = match_index_map[m.num]
            flipped = match_flip_map.get(m.num, False)
            if flipped:
                goals1[:, fi] = m.score2  # canonical t1 = data's team2
                goals2[:, fi] = m.score1
            else:
                goals1[:, fi] = m.score1
                goals2[:, fi] = m.score2

    # Sample unplayed group-stage matches
    unplayed_indices: list[int] = []
    lam1_list: list[float] = []
    lam2_list: list[float] = []
    base1_list: list[int] = []   # goals already scored in a live match (canonical)
    base2_list: list[int] = []

    for m in matches:
        if m.group and not m.is_played and m.num in match_index_map:
            fi = match_index_map[m.num]
            flipped = match_flip_map.get(m.num, False)
            # canonical t1 = data team2 when flipped
            t1_name = m.team2 if flipped else m.team1
            t2_name = m.team1 if flipped else m.team2
            override = match_lambda_overrides.get(m.num) if match_lambda_overrides else None
            if override is not None:
                # Bookmaker h2h-derived rates (stored for m.team1, m.team2).
                oa, ob = override
                lam1, lam2 = (ob, oa) if flipped else (oa, ob)
            else:
                p1 = team_params.get(t1_name)
                p2 = team_params.get(t2_name)
                if p1 and p2:
                    # Host advantage: a 2026 host playing in its own country gets +gamma.
                    h1 = ratings.HOME_ADV if host_playing_at_home(t1_name, m.ground) else 0.0
                    h2 = ratings.HOME_ADV if host_playing_at_home(t2_name, m.ground) else 0.0
                    lam1 = ratings.BASE_RATE * math.exp(p1.alpha - p2.beta + h1)
                    lam2 = ratings.BASE_RATE * math.exp(p2.alpha - p1.beta + h2)
                else:
                    lam1 = lam2 = ratings.BASE_RATE
            # Live match: fix the current score, sample only the remaining fraction.
            base1 = base2 = 0
            live = inplay.get(m.num) if inplay else None
            if live is not None:
                c1, c2, frac = live
                base1, base2 = (c2, c1) if flipped else (c1, c2)  # canonical orientation
                lam1 *= frac
                lam2 *= frac
            unplayed_indices.append(fi)
            lam1_list.append(lam1)
            lam2_list.append(lam2)
            base1_list.append(base1)
            base2_list.append(base2)

    if unplayed_indices:
        lam1_arr = np.array(lam1_list)
        lam2_arr = np.array(lam2_list)
        sampled1 = np.random.poisson(lam=lam1_arr, size=(n, len(lam1_list)))
        sampled2 = np.random.poisson(lam=lam2_arr, size=(n, len(lam2_list)))
        # Add goals already scored in any live matches (broadcast across sims).
        goals1[:, unplayed_indices] = sampled1 + np.array(base1_list, dtype=np.int32)
        goals2[:, unplayed_indices] = sampled2 + np.array(base2_list, dtype=np.int32)

    # --- Group stage standings ---
    ranks, pts, gd, gf = compute_group_standings(goals1, goals2, groups)

    # --- 3rd-place selection ---
    # Build per-team total goals scored (for player model)
    team_total_scored: dict[int, int] = {i: 0 for i in range(48)}
    for m in matches:
        if m.group and m.is_played:
            t1i = team_to_idx.get(m.team1, -1)
            t2i = team_to_idx.get(m.team2, -1)
            if t1i >= 0: team_total_scored[t1i] += m.score1 or 0
            if t2i >= 0: team_total_scored[t2i] += m.score2 or 0

    third_global, third_qualifiers = select_third_place_qualifiers(
        ranks, pts, gd, gf, global_team_ids
    )

    # Build third_qualifies (N, 48) bool
    third_qualifies = np.zeros((n, 48), dtype=bool)
    for slot_i in range(8):
        for ni in range(n):
            t = third_qualifiers[ni, slot_i]
            third_qualifies[ni, t] = True

    # --- Build fixed winners for played KO matches ---
    fixed_ko: dict[str, dict[int, int]] = {
        "R32": {}, "R16": {}, "QF": {}, "SF": {}, "Final": {}
    }
    for m in matches:
        if m.is_knockout and m.is_played and m.num in KO_MATCH_TO_BRACKET:
            s1, s2 = m.score1 or 0, m.score2 or 0
            if s1 == s2:
                continue  # penalty shootout -- ft score is tied
            round_name, bracket_pos = KO_MATCH_TO_BRACKET[m.num]
            winner_name = m.team1 if s1 > s2 else m.team2
            winner_idx = team_to_idx.get(winner_name, -1)
            if winner_idx >= 0 and round_name in fixed_ko:
                fixed_ko[round_name][bracket_pos] = winner_idx

    # --- Knockout bracket ---
    # Build (alpha, beta) dict for knockout lambdas
    ko_params: dict[int, tuple[float, float]] = {}
    for name, params in team_params.items():
        ti = team_to_idx.get(name, -1)
        if ti >= 0:
            ko_params[ti] = (params.alpha, params.beta)

    # Host-advantage venues per KO bracket position: a host playing a KO match
    # staged in its own country gets +HOME_ADV (applied to that team only).
    ko_host: dict[str, dict[int, int]] = {}
    for m in matches:
        if m.is_knockout and m.num in KO_MATCH_TO_BRACKET:
            country = VENUE_COUNTRY.get(m.ground)
            if country in HOSTS_2026:
                host_idx = team_to_idx.get(country, -1)
                if host_idx >= 0:
                    round_name, bracket_pos = KO_MATCH_TO_BRACKET[m.num]
                    ko_host.setdefault(round_name, {})[bracket_pos] = host_idx

    reach, ko_goals, ko_opp = simulate_knockout(
        ranks, global_team_ids, third_qualifiers, ko_params, team_to_idx,
        base_rate=ratings.BASE_RATE,
        fixed_ko=fixed_ko,
        home_adv=ratings.HOME_ADV,
        ko_host=ko_host,
    )

    # --- Player simulation ---
    # Expected remaining goals per team across sims
    team_remaining: dict[int, np.ndarray] = {}
    for g_idx, g in enumerate(group_order):
        local_teams = group_teams[g]
        for local_i, t_name in enumerate(local_teams):
            ti = team_to_idx[t_name]
            # Future group stage goals: sum over unplayed matches for this team
            rem = np.zeros(n, dtype=np.int32)
            for m in matches:
                if m.group == g and not m.is_played:
                    fi = match_index_map.get(m.num, -1)
                    if fi < 0:
                        continue
                    if m.team1 == t_name:
                        rem += goals1[:, fi]
                    elif m.team2 == t_name:
                        rem += goals2[:, fi]
            team_remaining[ti] = rem

    # Add per-sim knockout goals to team_remaining so player projections
    # include goals scored in R32 through the Final.
    for ti in range(48):
        if ti in team_remaining:
            team_remaining[ti] = team_remaining[ti] + ko_goals[:, ti]
        else:
            team_remaining[ti] = ko_goals[:, ti].copy()

    goals_arr, assists_arr = simulate_player_goals(
        players, team_remaining, team_total_scored
    )
    # --- Aggregate ---
    grp_odds = aggregator.group_odds(ranks, pts, gd, global_team_ids, team_names, group_order)

    tp_odds = aggregator.third_place_odds(
        ranks, pts, gd, third_qualifies, global_team_ids, team_names, group_order
    )

    ko_odds = aggregator.knockout_odds(reach, team_names)

    golden_boot, top_assists = aggregator.player_award_odds(
        goals_arr, assists_arr, players
    ) if goals_arr.size > 0 else ([], [])

    elapsed = time.perf_counter() - t0

    return SimulationResult(
        group_odds=grp_odds,
        third_place_odds=tp_odds,
        knockout_odds=ko_odds,
        golden_boot=golden_boot,
        top_assists=top_assists,
        n_simulations=n,
        elapsed_seconds=round(elapsed, 2),
        team_names=team_names,
        reach=reach,
        ko_opp=ko_opp,
    )
