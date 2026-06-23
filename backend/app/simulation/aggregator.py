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
