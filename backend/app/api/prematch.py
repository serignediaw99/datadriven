"""
Pre-match prediction for a specific upcoming match.

Returns: xG, scoreline matrix (top 25 most likely), over/unders, clean sheets, 1X2.
"""

import math

from fastapi import APIRouter, HTTPException

from app.models.dixon_coles import scoreline_matrix, derived_stats
from app.models.ratings import match_lambdas
from app.state import state

router = APIRouter()


@router.get("/matches")
async def list_matches():
    await state.ensure_loaded()
    result = []
    for m in state.matches:
        result.append({
            "id": m.num,
            "round": m.round,
            "group": m.group,
            "date": m.date,
            "team1": m.team1,
            "team2": m.team2,
            "score1": m.score1,
            "score2": m.score2,
            "status": "played" if m.is_played else "upcoming",
        })
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
        }

    p1 = state.team_params.get(match.team1)
    p2 = state.team_params.get(match.team2)

    if not p1 or not p2:
        raise HTTPException(422, "Team parameters not available")

    lam1, lam2 = match_lambdas(p1, p2)
    mat = scoreline_matrix(lam1, lam2)
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
        "team1": match.team1,
        "team2": match.team2,
        "xg_home": round(lam1, 2),
        "xg_away": round(lam2, 2),
        "top_scorelines": top_scorelines,
        **{k: round(v, 4) if isinstance(v, float) else v for k, v in stats.items()},
    }
