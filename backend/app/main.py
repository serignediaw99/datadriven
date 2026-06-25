"""
FastAPI application entry point.

Lifecycle:
  - On startup: load data + run initial 50k simulations
  - APScheduler polls OpenFootball every 5 minutes; re-sims on new results
  - CORS enabled for localhost:3000 (frontend)
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import standings, qualification, knockout, players, prematch, live, bracket, scenario
from app.state import state

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up — loading data and running initial simulations…")
    await state.ensure_loaded()

    # Poll for new results every 5 minutes (consumes the persisted ratings).
    scheduler.add_job(state.refresh, "interval", minutes=5, id="poll_data")
    # Refit the Dixon-Coles team-strength model once a day (heavy: re-scrapes
    # ~50k historical results and re-fits). Kick off an initial fit in the
    # background if none is persisted yet, so the app serves immediately.
    scheduler.add_job(state.refit_ratings, "interval", hours=24, id="refit_ratings")
    scheduler.start()
    log.info("Scheduler started (5-min poll, daily ratings refit)")

    if state.fitted_model is None:
        asyncio.create_task(state.refit_ratings())
        log.info("No persisted ratings — fitting Dixon-Coles model in background")

    yield

    scheduler.shutdown(wait=False)
    log.info("Shutting down")


app = FastAPI(title="WC 2026 Simulator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all route groups
app.include_router(standings.router,     prefix="/api")
app.include_router(qualification.router, prefix="/api")
app.include_router(knockout.router,      prefix="/api")
app.include_router(players.router,       prefix="/api")
app.include_router(prematch.router,      prefix="/api")
app.include_router(live.router,          prefix="/api")
app.include_router(bracket.router,       prefix="/api")
app.include_router(scenario.router,      prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "simulated": state.result is not None,
        "n_matches_played": sum(1 for m in state.matches if m.is_played),
    }


@app.post("/api/simulate")
async def trigger_simulation():
    """Manually trigger a data refresh + re-simulation (for testing)."""
    changed = await state.refresh()
    return {
        "changed": changed,
        "elapsed_seconds": state.result.elapsed_seconds if state.result else None,
    }


@app.post("/api/refit")
async def trigger_refit():
    """Manually refit the Dixon-Coles team-strength model (for testing)."""
    ok = await state.refit_ratings()
    m = state.fitted_model
    return {
        "refit": ok,
        "as_of": m.as_of.isoformat() if m else None,
        "n_matches": m.n_matches if m else None,
        "base_rate": round(m.base_rate(), 3) if m else None,
        "home_adv": round(m.gamma, 3) if m else None,
    }
