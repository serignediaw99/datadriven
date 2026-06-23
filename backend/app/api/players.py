from fastapi import APIRouter, HTTPException
from app.state import state
from app.simulation.aggregator import sort_player_awards

router = APIRouter()


@router.get("/awards/golden-boot")
async def get_golden_boot():
    await state.ensure_loaded()
    if not state.result:
        raise HTTPException(503, "Simulation not ready")
    return {
        "players": sort_player_awards(state.result.golden_boot),
        "n_simulations": state.result.n_simulations,
        "timestamp": state.result.timestamp,
    }


@router.get("/awards/assists")
async def get_top_assists():
    await state.ensure_loaded()
    if not state.result:
        raise HTTPException(503, "Simulation not ready")
    return {
        "players": sort_player_awards(state.result.top_assists),
        "n_simulations": state.result.n_simulations,
        "timestamp": state.result.timestamp,
    }
