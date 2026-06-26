"""
Server-Sent Events endpoint for live simulation updates.

Clients connect to GET /api/live/stream and receive:
  event: sim_update
  data: {"timestamp": <float>}

on every successful re-simulation triggered by new match results.
"""

import asyncio
import json
import logging

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.state import state

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/live/stream")
async def live_stream():
    queue = state.subscribe()

    async def generator():
        # Send a heartbeat immediately so the client knows we're alive
        yield {"event": "connected", "data": json.dumps({"status": "ok"})}
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {
                        "event": event.get("type", "update"),
                        # Forward the whole payload: just a timestamp for sim_update,
                        # full goal details for `goal` events.
                        "data": json.dumps({k: v for k, v in event.items() if k != "type"}),
                    }
                except asyncio.TimeoutError:
                    # Send a keepalive comment so proxies don't close idle connections
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            pass
        finally:
            state.unsubscribe(queue)

    return EventSourceResponse(generator())
