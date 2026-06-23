from fastapi import APIRouter, HTTPException
from app.state import state
from app.simulation import aggregator

router = APIRouter()


@router.get("/knockout")
async def get_knockout():
    await state.ensure_loaded()
    if not state.result:
        raise HTTPException(503, "Simulation not ready")
    return {
        "teams": state.result.knockout_odds,
        "n_simulations": state.result.n_simulations,
        "timestamp": state.result.timestamp,
    }


@router.get("/knockout/path/{team_name:path}")
async def get_path(team_name: str):
    await state.ensure_loaded()
    result = state.result
    if result is None:
        raise HTTPException(503, "Simulation not ready")
    if result.reach is None or result.ko_opp is None:
        raise HTTPException(503, "Path data not available")
    if team_name not in result.team_names:
        raise HTTPException(404, f"Team '{team_name}' not found")
    return aggregator.path_odds(result.reach, result.ko_opp, result.team_names, team_name)
