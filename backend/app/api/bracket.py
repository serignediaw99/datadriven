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
from app.simulation.third_place import THIRD_PLACE_SLOTS, _SLOT_ORDER

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
    Greedy group→slot assignment for the 8 3rd-place R32 slots.
    Rank groups by P(3rd qualifies), then assign each to the first eligible
    unoccupied slot in _SLOT_ORDER. One group per slot, one slot per group.
    """
    group_rank = sorted(
        [(-tpmap.get(f"Group {g}", {}).get("p_qualify_as_3rd", 0.0), g)
         for g in "ABCDEFGHIJKL"]
    )
    assigned: set[str] = set()
    slot_to_team: dict[int, str] = {}
    for match_num in _SLOT_ORDER:
        eligible = THIRD_PLACE_SLOTS[match_num]
        slot_i   = _MATCH_TO_SLOT_IDX[match_num]
        for _, letter in group_rank:
            if letter in assigned or letter not in eligible:
                continue
            teams = gmap.get(f"Group {letter}", [])
            if teams:
                best = max(teams, key=lambda t: t["p_3rd"])
                slot_to_team[slot_i] = best["team"]
                assigned.add(letter)
            break
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

    # R32
    r32: list[dict] = []
    r32_w: list[str] = []
    for mi, (da, db) in enumerate(R32_STRUCTURE):
        ta = _resolve(da, g1, g2, tp3)
        tb = _resolve(db, g1, g2, tp3)
        res = _match(ta, tb, params)
        r32.append({"id": mi, "match_num": 73 + mi, **res})
        r32_w.append(res["winner"])

    # R16
    r16: list[dict] = []
    r16_w: list[str] = []
    for ri, (ia, ib) in enumerate(R16_BRACKET):
        res = _match(r32_w[ia], r32_w[ib], params)
        r16.append({"id": ri, "r32_a": ia, "r32_b": ib, **res})
        r16_w.append(res["winner"])

    # QF
    qf: list[dict] = []
    qf_w: list[str] = []
    for qi, (ia, ib) in enumerate(QF_BRACKET):
        res = _match(r16_w[ia], r16_w[ib], params)
        qf.append({"id": qi, "r16_a": ia, "r16_b": ib, **res})
        qf_w.append(res["winner"])

    # SF
    sf: list[dict] = []
    sf_w: list[str] = []
    for si, (ia, ib) in enumerate(SF_BRACKET):
        res = _match(qf_w[ia], qf_w[ib], params)
        sf.append({"id": si, "qf_a": ia, "qf_b": ib, **res})
        sf_w.append(res["winner"])

    return {
        "r32": r32, "r16": r16, "qf": qf, "sf": sf,
        "final": _match(sf_w[0], sf_w[1], params),
    }
