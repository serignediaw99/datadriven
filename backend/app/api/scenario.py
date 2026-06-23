"""
Scenario explorer: run a quick one-off simulation with match result overrides.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.data.openfootball import WCMatch
from app.state import state
from app.simulation.engine import run as run_simulation
from app.simulation import aggregator

router = APIRouter()


class MatchOverride(BaseModel):
    match_num: int
    score1: int
    score2: int


class ScenarioRequest(BaseModel):
    overrides: list[MatchOverride]
    n_sims: int = 20_000
    focus_team: Optional[str] = None


@router.post("/scenario")
async def explore_scenario(request: ScenarioRequest):
    await state.ensure_loaded()
    if state.result is None:
        raise HTTPException(503, "Simulation not ready")

    n = max(1_000, min(request.n_sims, 50_000))
    override_map = {o.match_num: (o.score1, o.score2) for o in request.overrides}

    patched: list[WCMatch] = []
    for m in state.matches:
        if m.num in override_map:
            s1, s2 = override_map[m.num]
            patched.append(WCMatch(
                num=m.num, round=m.round, date=m.date,
                team1=m.team1, team2=m.team2,
                score1=s1, score2=s2,
                group=m.group,
                goals1=m.goals1, goals2=m.goals2,
                ground=m.ground,
            ))
        else:
            patched.append(m)

    result = run_simulation(patched, state.team_params, [], n=n)

    path = None
    if request.focus_team and result.reach is not None and result.ko_opp is not None:
        path = aggregator.path_odds(
            result.reach, result.ko_opp, result.team_names, request.focus_team
        )

    return {
        "group_odds": result.group_odds,
        "knockout_odds": result.knockout_odds,
        "path": path,
        "n_simulations": result.n_simulations,
        "elapsed_seconds": result.elapsed_seconds,
    }
