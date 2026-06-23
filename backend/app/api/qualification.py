from fastapi import APIRouter, HTTPException
from app.state import state

router = APIRouter()


@router.get("/third-place")
async def get_third_place():
    await state.ensure_loaded()
    if not state.result:
        raise HTTPException(503, "Simulation not ready")
    return {
        "third_place": state.result.third_place_odds,
        "n_simulations": state.result.n_simulations,
        "timestamp": state.result.timestamp,
    }
