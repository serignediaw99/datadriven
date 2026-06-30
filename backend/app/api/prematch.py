"""
Pre-match prediction for a specific upcoming match.

Returns: xG, scoreline matrix (top 25 most likely), over/unders, clean sheets, 1X2.
"""

import math

from fastapi import APIRouter, HTTPException

from app.data.metadata import host_playing_at_home
from app.models import ratings
from app.models.dixon_coles import RHO, scoreline_matrix, derived_stats
from app.state import state

router = APIRouter()


def _ko_result(m) -> dict:
    """Decisive-winner context for a played knockout match (empty for group games or
    matches decided in normal time). Surfaces the shootout/extra-time advancer so the
    UI can show a winner when the full-time score is level."""
    if not (m.is_knockout and m.is_played):
        return {}
    out: dict = {}
    winner = m.knockout_winner()
    if winner:
        out["winner"] = winner
    if m.pen1 is not None and m.pen2 is not None:
        out["pens1"] = m.pen1
        out["pens2"] = m.pen2
        out["decided_by"] = "pens"
    elif m.et1 is not None and m.et2 is not None:
        out["decided_by"] = "aet"
    return out


def _prediction_lambdas(match) -> tuple[float, float]:
    """Goal rates for an upcoming match, matching exactly what the simulation
    samples for it: the bookmaker h2h override if one is priced, otherwise the
    host-advantage-adjusted model rates (in data orientation: team1, team2)."""
    override = state.match_overrides.get(match.num)
    if override is not None:
        return override
    p1 = state.team_params[match.team1]
    p2 = state.team_params[match.team2]
    h1 = ratings.HOME_ADV if host_playing_at_home(match.team1, match.ground) else 0.0
    h2 = ratings.HOME_ADV if host_playing_at_home(match.team2, match.ground) else 0.0
    lam1 = ratings.BASE_RATE * math.exp(p1.alpha - p2.beta + h1)
    lam2 = ratings.BASE_RATE * math.exp(p2.alpha - p1.beta + h2)
    return lam1, lam2


@router.get("/matches")
async def list_matches():
    await state.ensure_loaded()
    result = []
    for m in state.matches:
        entry = {
            "id": m.num,
            "round": m.round,
            "group": m.group,
            "date": m.date,
            "venue": m.ground or None,
            "team1": m.team1,
            "team2": m.team2,
            "score1": m.score1,
            "score2": m.score2,
            "status": "played" if m.is_played else "upcoming",
            **_ko_result(m),
        }
        # Overlay the live ESPN score/state (ahead of the slower OpenFootball feed).
        live = state.live_status.get(m.num)
        if live is not None and not m.is_played:
            entry["score1"] = live["score1"]
            entry["score2"] = live["score2"]
            entry["status"] = "live" if live["state"] == "in" else "played"
            entry["live_minute"] = live["minute"]
            entry["live_status"] = live["status"]
        result.append(entry)
    return {"matches": result}


@router.get("/matches/{match_id}/prediction")
async def get_prediction(match_id: int):
    await state.ensure_loaded()

    match = next((m for m in state.matches if m.num == match_id), None)
    if match is None:
        raise HTTPException(404, f"Match {match_id} not found")

    if match.is_played:
        return {
            "match_id": match_id,
            "status": "played",
            "result": f"{match.score1}-{match.score2}",
            "team1": match.team1,
            "team2": match.team2,
            "venue": match.ground or None,
            **_ko_result(match),
        }

    if match.team1 not in state.team_params or match.team2 not in state.team_params:
        raise HTTPException(422, "Team parameters not available")

    lam1, lam2 = _prediction_lambdas(match)
    rho = state.fitted_model.rho if state.fitted_model is not None else RHO
    mat = scoreline_matrix(lam1, lam2, rho=rho)
    stats = derived_stats(mat)

    # Full 8×8 scoreline matrix (row = home goals, col = away goals)
    top_scorelines = [
        {"score": f"{g1}-{g2}", "probability": round(float(mat[g1, g2]), 4)}
        for g1 in range(8) for g2 in range(8)
    ]

    return {
        "match_id": match_id,
        "status": "upcoming",
        "date": match.date,
        "venue": match.ground or None,
        "team1": match.team1,
        "team2": match.team2,
        "xg_home": round(lam1, 2),
        "xg_away": round(lam2, 2),
        "top_scorelines": top_scorelines,
        **{k: round(v, 4) if isinstance(v, float) else v for k, v in stats.items()},
    }
