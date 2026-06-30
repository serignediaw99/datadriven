"""
Shareable knockout-stage insight endpoints (built for screenshot-friendly graphics):

  GET /api/insights/final   -- most likely Final matchups + finalist heatmap
  GET /api/insights/road    -- 'strength of path' / easiest-vs-hardest road to the Final
  GET /api/insights/movers  -- championship-odds movers since the knockouts began
"""
import numpy as np
from fastapi import APIRouter, HTTPException

from app.state import state
from app.simulation import aggregator

router = APIRouter()


def _power_vector(team_names: list[str]) -> np.ndarray:
    """
    A 0-100 opponent power rating per team (aligned to team_names), derived from the
    Dixon-Coles attack+defence strength (alpha + beta) min-max scaled across the field.
    """
    raw = np.zeros(len(team_names), dtype=np.float64)
    for i, name in enumerate(team_names):
        p = state.team_params.get(name)
        raw[i] = (p.alpha + p.beta) if p is not None else 0.0
    lo, hi = float(raw.min()), float(raw.max())
    if hi - lo < 1e-9:
        return np.full(len(team_names), 75.0)
    return 50.0 + 50.0 * (raw - lo) / (hi - lo)


@router.get("/insights/final")
async def get_final_matchups():
    await state.ensure_loaded()
    r = state.result
    if r is None or r.reach is None:
        raise HTTPException(503, "Simulation not ready")
    data = aggregator.final_matchups(r.reach, r.team_names)
    return {**data, "n_simulations": r.n_simulations, "timestamp": r.timestamp}


@router.get("/insights/road")
async def get_road_to_final():
    await state.ensure_loaded()
    r = state.result
    if r is None or r.reach is None or r.ko_opp is None:
        raise HTTPException(503, "Simulation not ready")
    power = _power_vector(r.team_names)
    data = aggregator.road_to_final(r.reach, r.ko_opp, r.team_names, power)
    return {**data, "n_simulations": r.n_simulations, "timestamp": r.timestamp}


@router.get("/insights/movers")
async def get_title_movers():
    await state.ensure_loaded()
    r = state.result
    if r is None:
        raise HTTPException(503, "Simulation not ready")
    return state.title_movers()
