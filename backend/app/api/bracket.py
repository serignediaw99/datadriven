"""
Projected tournament bracket: most-likely team per slot and win probabilities.

Constraints enforced:
  1. Each group's 1st and 2nd place slots are given to DIFFERENT teams.
  2. 3rd-place slots use a globally-consistent greedy group→slot assignment,
     so no group (and no team) appears in more than one 3rd-place slot.
"""
import math
from fastapi import APIRouter, HTTPException
from app.state import state
from app.simulation.knockout import R32_STRUCTURE, R16_BRACKET, QF_BRACKET, SF_BRACKET
from app.simulation.third_place import (
    THIRD_PLACE_SLOTS, _SLOT_ORDER, _THIRD_PLACE_ASSIGNMENT, _GROUP_LETTERS,
)

router = APIRouter()

BASE = 1.15
_SLOT_IDX_TO_MATCH = list(_SLOT_ORDER)           # [74,77,79,80,81,82,85,87]
_MATCH_TO_SLOT_IDX = {m: i for i, m in enumerate(_SLOT_IDX_TO_MATCH)}


def _win_prob(alpha_a, beta_a, alpha_b, beta_b, max_k=12):
    lam_a = BASE * math.exp(alpha_a - beta_b)
    lam_b = BASE * math.exp(alpha_b - beta_a)
    def pmf(lam, k): return math.exp(-lam) * (lam**k) / math.factorial(k)
    p_win = p_tie = px_cdf = 0.0
    for k in range(max_k + 1):
        px_k = pmf(lam_a, k); py_k = pmf(lam_b, k)
        px_cdf += px_k
        p_win += (1.0 - px_cdf) * py_k
        p_tie += px_k * py_k
    return p_win + 0.5 * p_tie


def _build_group_slots(gmap: dict) -> tuple[dict, dict]:
    """
    For each group letter, return the most likely distinct 1st and 2nd place teams.
    The 2nd-place pick explicitly excludes whoever was picked for 1st.
    """
    g1: dict[str, str] = {}   # letter → most-likely 1st-place team
    g2: dict[str, str] = {}   # letter → most-likely 2nd-place team (≠ g1)
    for letter in "ABCDEFGHIJKL":
        teams = gmap.get(f"Group {letter}", [])
        if not teams:
            g1[letter] = g2[letter] = "TBD"
            continue
        by_1st = sorted(teams, key=lambda t: -t["p_1st"])
        g1[letter] = by_1st[0]["team"]
        by_2nd = sorted(teams, key=lambda t: -t["p_2nd"])
        for t in by_2nd:
            if t["team"] != g1[letter]:
                g2[letter] = t["team"]
                break
        else:
            g2[letter] = by_2nd[0]["team"]
    return g1, g2


def _assign_third_place(tpmap: dict, gmap: dict) -> dict[int, str]:
    """
    Assign the 8 best 3rd-place groups to the R32 third-place slots, mirroring the
    simulation (third_place.select_third_place_qualifiers) so the projected bracket
    matches the simulated R32 matchups shown on the Path/odds pages.

    Two things must match the sim, or the bracket diverges from the odds:
      1. Restrict to the 8 groups most likely to finish as a qualifying 3rd-place
         team. A group outside that top 8 must NOT appear in the bracket (otherwise
         a team that won't even qualify, e.g. a 4th-likely 3rd-placer, gets slotted).
      2. Fill slots by iterating eligible qualifying groups in LETTER order (A-L) —
         the simulation iterates them A-L, not by P(qualify).
    """
    letters = "ABCDEFGHIJKL"
    p_qual = {L: tpmap.get(f"Group {L}", {}).get("p_qualify_as_3rd", 0.0) for L in letters}
    top8 = sorted(letters, key=lambda L: -p_qual[L])[:8]
    combo = frozenset(letters.index(L) for L in top8)

    slot_to_team: dict[int, str] = {}
    assignment = _THIRD_PLACE_ASSIGNMENT.get(combo)  # {slot_match_num: group_idx}
    if assignment is None:
        return slot_to_team
    for match_num, gi in assignment.items():
        teams = gmap.get(f"Group {_GROUP_LETTERS[gi]}", [])
        if teams:
            best = max(teams, key=lambda t: t["p_3rd"])
            slot_to_team[_MATCH_TO_SLOT_IDX[match_num]] = best["team"]
    return slot_to_team


def _resolve(desc: str, g1: dict, g2: dict, tp3: dict[int, str]) -> str:
    kind, val = desc.split(":", 1)
    if kind == "team": return val
    if kind == "1":    return g1.get(val, "TBD")
    if kind == "2":    return g2.get(val, "TBD")
    if kind == "3":    return tp3.get(int(val), "TBD")
    return "TBD"


def _match(ta: str, tb: str, params: dict) -> dict:
    pa, pb = params.get(ta), params.get(tb)
    pw = _win_prob(pa.alpha, pa.beta, pb.alpha, pb.beta) if pa and pb else 0.5
    return {
        "team_a": ta, "team_b": tb,
        "winner":    ta if pw >= 0.5 else tb,
        "p_win":     round(max(pw, 1 - pw), 3),
        "p_a_wins":  round(pw, 3),
    }


@router.get("/bracket")
async def get_bracket():
    await state.ensure_loaded()
    if not state.result:
        raise HTTPException(503, "Simulation not ready")

    gmap   = {g["group"]: g["teams"] for g in state.result.group_odds}
    tpmap  = {tp["group"]: tp        for tp in state.result.third_place_odds}
    params = state.team_params

    g1, g2  = _build_group_slots(gmap)
    tp3     = _assign_third_place(tpmap, gmap)

    # Venue per knockout match number (R32 73-88, R16 89-96, QF 97-100, SF 101-102,
    # Final 104) from the fixture data.
    venues = {m.num: (m.ground or None) for m in state.matches}

    # R32
    r32: list[dict] = []
    r32_w: list[str] = []
    for mi, (da, db) in enumerate(R32_STRUCTURE):
        ta = _resolve(da, g1, g2, tp3)
        tb = _resolve(db, g1, g2, tp3)
        res = _match(ta, tb, params)
        r32.append({"id": mi, "match_num": 73 + mi, "venue": venues.get(73 + mi), **res})
        r32_w.append(res["winner"])

    # R16
    r16: list[dict] = []
    r16_w: list[str] = []
    for ri, (ia, ib) in enumerate(R16_BRACKET):
        res = _match(r32_w[ia], r32_w[ib], params)
        r16.append({"id": ri, "match_num": 89 + ri, "venue": venues.get(89 + ri),
                    "r32_a": ia, "r32_b": ib, **res})
        r16_w.append(res["winner"])

    # QF
    qf: list[dict] = []
    qf_w: list[str] = []
    for qi, (ia, ib) in enumerate(QF_BRACKET):
        res = _match(r16_w[ia], r16_w[ib], params)
        qf.append({"id": qi, "match_num": 97 + qi, "venue": venues.get(97 + qi),
                   "r16_a": ia, "r16_b": ib, **res})
        qf_w.append(res["winner"])

    # SF
    sf: list[dict] = []
    sf_w: list[str] = []
    for si, (ia, ib) in enumerate(SF_BRACKET):
        res = _match(qf_w[ia], qf_w[ib], params)
        sf.append({"id": si, "match_num": 101 + si, "venue": venues.get(101 + si),
                   "qf_a": ia, "qf_b": ib, **res})
        sf_w.append(res["winner"])

    return {
        "r32": r32, "r16": r16, "qf": qf, "sf": sf,
        "final": {"match_num": 104, "venue": venues.get(104), **_match(sf_w[0], sf_w[1], params)},
    }
