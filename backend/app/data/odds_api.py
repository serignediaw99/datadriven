"""
The Odds API client (bookmaker odds blend, Phase 2).

Pulls two free-tier markets for the FIFA World Cup:
  - outright winner odds  (sport `soccer_fifa_world_cup_winner`, market `outrights`)
  - per-match h2h odds     (sport `soccer_fifa_world_cup`,        market `h2h`)

The API key is read ONLY from the environment variable ``ODDS_API_KEY`` and is
never hardcoded or logged. The whole module is best-effort: if the key is unset,
the network fails, or the quota is exhausted, the fetchers return ``None`` and the
simulator silently falls back to the pure model.

Responses are disk-cached with a moderate TTL so the daily refit stays well inside
the free plan's monthly request quota; the ``x-requests-remaining`` header is logged
on every live call.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4/sports"
SPORT_WINNER = "soccer_fifa_world_cup_winner"
SPORT_MATCH = "soccer_fifa_world_cup"
REGIONS = "us,uk,eu"

OUTRIGHTS_CACHE = "odds_outrights.json"
H2H_CACHE = "odds_h2h.json"
DEFAULT_TTL = 6 * 3600  # 6h — odds drift slowly; daily refit consumes ~2 calls/day


def api_key() -> Optional[str]:
    """Return the Odds API key from the environment, or None if unset/blank."""
    key = os.environ.get("ODDS_API_KEY", "").strip()
    return key or None


def enabled() -> bool:
    """The odds blend is opt-in: active only when ODDS_API_KEY is set."""
    return api_key() is not None


def _cache_fresh(path: str, ttl: int) -> Optional[list]:
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return None
    if age > ttl:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _read_cache(path: str) -> Optional[list]:
    """Read a cached payload regardless of age (stale-but-usable fallback)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


async def _fetch(
    session: aiohttp.ClientSession,
    sport: str,
    markets: str,
    cache_path: str,
    ttl: int,
    force: bool,
) -> Optional[list]:
    if not force:
        cached = _cache_fresh(cache_path, ttl)
        if cached is not None:
            return cached

    key = api_key()
    if key is None:
        return _read_cache(cache_path)  # disabled — serve stale if present

    url = f"{BASE_URL}/{sport}/odds/"
    params = {"regions": REGIONS, "markets": markets, "apiKey": key}
    try:
        async with session.get(url, params=params, timeout=30) as resp:
            remaining = resp.headers.get("x-requests-remaining")
            used = resp.headers.get("x-requests-used")
            if resp.status != 200:
                body = (await resp.text())[:200]
                log.warning("Odds API %s -> HTTP %d: %s", sport, resp.status, body)
                return _read_cache(cache_path)
            data = await resp.json()
            log.info(
                "Odds API %s/%s ok (%d events); quota remaining=%s used=%s",
                sport, markets, len(data) if isinstance(data, list) else 0,
                remaining, used,
            )
    except (aiohttp.ClientError, ValueError, TimeoutError) as e:
        log.warning("Odds API %s fetch failed: %s", sport, e)
        return _read_cache(cache_path)

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass
    return data


async def fetch_outrights(
    session: aiohttp.ClientSession, ttl: int = DEFAULT_TTL, force: bool = False
) -> Optional[list]:
    """Raw outright-winner payload (list of one event) or None."""
    return await _fetch(session, SPORT_WINNER, "outrights", OUTRIGHTS_CACHE, ttl, force)


async def fetch_h2h(
    session: aiohttp.ClientSession, ttl: int = DEFAULT_TTL, force: bool = False
) -> Optional[list]:
    """Raw per-match h2h payload (list of upcoming match events) or None."""
    return await _fetch(session, SPORT_MATCH, "h2h", H2H_CACHE, ttl, force)
