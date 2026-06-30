"""
Convert raw simulation arrays into probability dictionaries for the API layer.
"""

from __future__ import annotations

import numpy as np


def group_odds(
    ranks: np.ndarray,          # (N, 12, 4)
    pts: np.ndarray,            # (N, 12, 4)
    gd: np.ndarray,             # (N, 12, 4)
    global_team_ids: np.ndarray,  # (12, 4)  global idx per (group, local)
    team_names: list[str],        # 48 names by global idx
    group_names: list[str],       # 12 group names
) -> list[dict]:
    """
    Returns a list of group dicts:
      [{name, teams: [{name, p_1st, p_2nd, p_3rd, p_out, avg_pts, avg_gd}]}]
    """
    N = ranks.shape[0]
    result = []
    for g, grp_name in enumerate(group_names):
        team_rows = []
        for local in range(4):
            t_global = int(global_team_ids[g, local])
            name = team_names[t_global]

            # Position counts: how often this local team finishes at each rank
            p_pos = np.zeros(4)
            for r in range(4):
                p_pos[r] = float((ranks[:, g, r] == local).sum()) / N

            # Average pts and GD for this team
            avg_pts = float(pts[:, g, local].mean())
            avg_gd  = float(gd[:, g, local].mean())

            team_rows.append({
                "team": name,
                "p_1st":  round(p_pos[0], 4),
                "p_2nd":  round(p_pos[1], 4),
                "p_3rd":  round(p_pos[2], 4),
                "p_4th":  round(p_pos[3], 4),
                "avg_pts": round(avg_pts, 2),
                "avg_gd":  round(avg_gd, 2),
            })

        team_rows.sort(key=lambda r: -r["avg_pts"])
        result.append({"group": grp_name, "teams": team_rows})
    return result


def third_place_odds(
    ranks: np.ndarray,          # (N, 12, 4)
    pts: np.ndarray,            # (N, 12, 4)
    gd: np.ndarray,             # (N, 12, 4)
    third_qualifies: np.ndarray, # (N, 48) bool — does each team qualify as 3rd?
    global_team_ids: np.ndarray,
    team_names: list[str],
    group_names: list[str],
) -> list[dict]:
    """
    Per-group: 3rd-place team qualification odds and pts/GD thresholds.
    """
    N = ranks.shape[0]
    result = []
    for g, grp_name in enumerate(group_names):
        # 3rd-place finisher in this group across sims
        third_local = ranks[:, g, 2]  # (N,) local team index of 3rd place
        t_globals = global_team_ids[g, third_local]  # (N,) global idx

        # Pts and GD of the 3rd-place team
        third_pts = pts[np.arange(N), g, third_local]
        third_gd  = gd [np.arange(N), g, third_local]

        # Qualification rate: how often each group's 3rd-place qualifies
        qualifies_mask = np.array([third_qualifies[n, t_globals[n]] for n in range(N)])
        p_qualify = float(qualifies_mask.sum() / N)

        result.append({
            "group": grp_name,
            "p_qualify_as_3rd": round(p_qualify, 4),
            "pts_needed_p50": int(np.percentile(third_pts[qualifies_mask], 50)) if qualifies_mask.any() else None,
            "pts_needed_p75": int(np.percentile(third_pts[qualifies_mask], 25)) if qualifies_mask.any() else None,
            "gd_needed_p50":  int(np.percentile(third_gd [qualifies_mask], 50)) if qualifies_mask.any() else None,
        })
    return result


def knockout_odds(
    reach: np.ndarray,     # (N, 48, 6)
    team_names: list[str],
) -> list[dict]:
    """
    Per-team: P(reach R32/R16/QF/SF/Final/Win), top-3 opponents per round.
    """
    N = reach.shape[0]
    round_labels = ["R32", "R16", "QF", "SF", "Final", "Winner"]
    result = []
    for t, name in enumerate(team_names):
        if reach[:, t, :].sum() == 0:
            continue  # team never appears in any sim (shouldn't happen)
        probs = {
            round_labels[r]: round(float(reach[:, t, r].mean()), 4)
            for r in range(6)
        }
        result.append({"team": name, "probs": probs})
    result.sort(key=lambda r: -r["probs"]["Winner"])
    return result


def sort_player_awards(rows: list[dict]) -> list[dict]:
    """Sort by current tally, then projected total."""
    return sorted(rows, key=lambda r: (-r["current"], -r["expected_total"]))


def player_award_odds(
    goals_arr: np.ndarray,    # (N, P)
    assists_arr: np.ndarray,  # (N, P)
    players: list,            # list[PlayerEntry] — for current_goals/current_assists
    top_n: int = 20,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (golden_boot_list, assists_list) each sorted by current tally,
    then projected total (expected_total).
    """
    N, P = goals_arr.shape

    # Golden boot: player with most goals in sim
    boot_winner = np.argmax(goals_arr, axis=1)  # (N,)
    boot_probs = np.bincount(boot_winner, minlength=P) / N

    # Most assists: player with most assists
    ast_winner = np.argmax(assists_arr, axis=1)
    ast_probs = np.bincount(ast_winner, minlength=P) / N

    def _rows(arr: np.ndarray, probs: np.ndarray, current_vals: list) -> list[dict]:
        rows = []
        for p, player in enumerate(players):
            avg = float(arr[:, p].mean())
            rows.append({
                "player": player.name,
                "team": player.team,
                "current": current_vals[p],
                "expected_total": round(avg, 2),
                "p_win": round(float(probs[p]), 4),
                "p_top5": round(float((arr[:, p] >= np.sort(arr, axis=1)[:, -5]).mean()), 4),
            })
        return sort_player_awards(rows)[:top_n]

    current_goals   = [p.current_goals   for p in players]
    current_assists = [p.current_assists  for p in players]
    return _rows(goals_arr, boot_probs, current_goals), _rows(assists_arr, ast_probs, current_assists)


def path_odds(
    reach: np.ndarray,       # (N, 48, 6) bool
    ko_opp: np.ndarray,      # (N, 48, 6) int8, -1 = did not play
    team_names: list[str],
    team_name: str,
    top_n: int = 6,
) -> dict:
    """
    For a given team, return the most likely opponents in each KO round.
    Round labels match reach: R32, R16, QF, SF, Final (rounds 0-4).
    """
    if team_name not in team_names:
        return {"team": team_name, "path": {}}

    t = team_names.index(team_name)
    round_labels = ["R32", "R16", "QF", "SF", "Final"]

    path: dict[str, list[dict]] = {}
    for r, label in enumerate(round_labels):
        sims_reached = reach[:, t, r]      # (N,) bool
        total = int(sims_reached.sum())
        if total == 0:
            path[label] = []
            continue

        opponents = ko_opp[sims_reached, t, r].astype(np.int32)  # signed expand
        unique_opps, counts = np.unique(opponents[opponents >= 0], return_counts=True)
        sorted_idx = np.argsort(-counts)

        opp_list = []
        for idx in sorted_idx[:top_n]:
            opp_idx = int(unique_opps[idx])
            cnt = int(counts[idx])
            opp_list.append({
                "opponent": team_names[opp_idx],
                "p": round(cnt / total, 4),
            })
        path[label] = opp_list

    return {"team": team_name, "path": path}


def final_matchups(
    reach: np.ndarray,       # (N, 48, 6) bool
    team_names: list[str],
    top_n: int = 12,
) -> dict:
    """
    Probability of each possible Final matchup, derived directly from the reach
    array: exactly two teams reach round 4 (the Final) in every sim, so the joint
    P(A and B both reach the Final) IS P(the Final is A vs B).

    Returns the most likely finals plus a heatmap. The bracket guarantees the two
    finalists come from opposite halves, so the finalist set is 2-colourable into
    the two halves (BFS over the co-finalist graph) -- one half becomes the heatmap
    rows, the other the columns, so no cell is a structurally-impossible same-half
    pairing.
    """
    N = reach.shape[0]
    fin = reach[:, :, 4]                       # (N, 48) finalist flags
    p_final = fin.mean(axis=0)                 # (48,)
    finalists = [t for t in range(len(team_names)) if p_final[t] > 0]

    # Pairwise finalist probabilities (cross-half pairs only have non-zero counts).
    pair_p: dict[tuple[int, int], float] = {}
    adj: dict[int, set[int]] = {t: set() for t in finalists}
    pairs: list[tuple[int, int, float]] = []
    for ii in range(len(finalists)):
        a = finalists[ii]
        fa = fin[:, a]
        for jj in range(ii + 1, len(finalists)):
            b = finalists[jj]
            cnt = int(np.count_nonzero(fa & fin[:, b]))
            if cnt > 0:
                p = cnt / N
                pair_p[(a, b)] = p
                adj[a].add(b)
                adj[b].add(a)
                pairs.append((a, b, p))

    pairs.sort(key=lambda x: -x[2])
    most_likely = [
        {"team_a": team_names[a], "team_b": team_names[b], "p": round(p, 4)}
        for a, b, p in pairs[:top_n]
    ]

    # 2-colour the co-finalist graph into the two bracket halves.
    color: dict[int, int] = {}
    for start in finalists:
        if start in color:
            continue
        color[start] = 0
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in color:
                    color[v] = color[u] ^ 1
                    stack.append(v)

    rows = sorted([t for t in finalists if color.get(t, 0) == 0], key=lambda t: -p_final[t])
    cols = sorted([t for t in finalists if color.get(t, 0) == 1], key=lambda t: -p_final[t])

    def _pair(a: int, b: int) -> float:
        return pair_p.get((a, b)) or pair_p.get((b, a)) or 0.0

    matrix = [[round(_pair(r, c), 4) for c in cols] for r in rows]

    return {
        "most_likely": most_likely,
        "heatmap": {
            "rows": [{"team": team_names[t], "p_final": round(float(p_final[t]), 4)} for t in rows],
            "cols": [{"team": team_names[t], "p_final": round(float(p_final[t]), 4)} for t in cols],
            "matrix": matrix,
        },
    }


def road_to_final(
    reach: np.ndarray,       # (N, 48, 6) bool
    ko_opp: np.ndarray,      # (N, 48, 6) int8, -1 = did not play
    team_names: list[str],
    power: np.ndarray,       # (48,) opponent power rating, ~0-100 scale
) -> dict:
    """
    'Strength of path' for every team still alive: the probability-weighted average
    power rating of the opponents it is projected to face from the Round of 32 through
    the Final (rounds 0-4). Lower = easier road. Per-round detail gives each round's
    reach probability, most-likely opponent, and average opponent power.

    A team is 'alive' if it can still reach the Round of 16 (P(R16) > 0), which
    excludes teams already knocked out in the Round of 32. The R32 leg is included
    because for most teams it is still their next (or an in-progress) match.
    """
    round_idx = [0, 1, 2, 3, 4]
    round_labels = ["R32", "R16", "QF", "SF", "Final"]
    out: list[dict] = []

    for t in range(len(team_names)):
        if reach[:, t, 1].mean() <= 0:
            continue  # eliminated in R32 (or not a knockout team)

        rounds: list[dict] = []
        num = 0.0
        den = 0.0
        for ri, label in zip(round_idx, round_labels):
            mask = reach[:, t, ri]
            p_reach = float(mask.mean())
            if p_reach <= 0:
                rounds.append({"round": label, "p_reach": 0.0,
                               "opp_power": None, "likely_opp": None, "likely_opp_p": None})
                continue
            opps = ko_opp[mask, t, ri].astype(np.int32)
            opps = opps[opps >= 0]
            if opps.size == 0:
                rounds.append({"round": label, "p_reach": round(p_reach, 4),
                               "opp_power": None, "likely_opp": None, "likely_opp_p": None})
                continue
            opp_power = float(power[opps].mean())
            uo, cnt = np.unique(opps, return_counts=True)
            k = int(np.argmax(cnt))
            num += p_reach * opp_power
            den += p_reach
            rounds.append({
                "round": label,
                "p_reach": round(p_reach, 4),
                "opp_power": round(opp_power, 1),
                "likely_opp": team_names[int(uo[k])],
                "likely_opp_p": round(int(cnt[k]) / opps.size, 4),
            })

        out.append({
            "team": team_names[t],
            "difficulty": round(num / den, 1) if den > 0 else 0.0,
            "p_reach_final": round(float(reach[:, t, 4].mean()), 4),
            "exp_games_remaining": round(den, 2),
            "rounds": rounds,
        })

    out.sort(key=lambda r: r["difficulty"])  # easiest road first
    return {"teams": out}
