from fastapi import APIRouter, HTTPException
from app.state import state

router = APIRouter()


@router.get("/groups")
async def get_groups():
    await state.ensure_loaded()
    if not state.result:
        raise HTTPException(503, "Simulation not ready")
    return {
        "groups": state.result.group_odds,
        "n_simulations": state.result.n_simulations,
        "timestamp": state.result.timestamp,
    }
