"""
Historical international match results — training data for the team-strength model.

Source: martj42/international_results (`results.csv`), 1872-present, ~49k matches
(friendlies, qualifiers, continental cups, World Cups), with a neutral-venue flag.
Free, no auth, regularly updated.

The raw CSV is cached on disk next to cache.db with a long TTL. Fetching is
best-effort: on a network failure we fall back to the (possibly stale) cached
copy, mirroring the graceful-degradation pattern used elsewhere in app/data.
"""

from __future__ import annotations

import io
import os
import time
from typing import Optional

import aiohttp
import pandas as pd

RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)

# Cache the raw CSV on disk (cwd-relative, like cache.db). 24h default TTL.
CACHE_PATH = "intl_results.csv"
DEFAULT_TTL = 24 * 3600

# martj42 spelling -> canonical (openfootball / app) spelling. Only the WC-2026
# finalists that differ need an entry; every other finalist already matches.
RESULTS_TO_CANONICAL: dict[str, str] = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
}


def to_canonical(name: str) -> str:
    return RESULTS_TO_CANONICAL.get(name, name)


def _clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse types, drop unplayed rows, canonicalise team names."""
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df = df.dropna(subset=["date", "home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df["home_team"] = df["home_team"].map(to_canonical)
    df["away_team"] = df["away_team"].map(to_canonical)
    # `neutral` may arrive as bool or as the strings "TRUE"/"FALSE".
    if df["neutral"].dtype != bool:
        df["neutral"] = (
            df["neutral"].astype(str).str.strip().str.upper().eq("TRUE")
        )
    cols = [
        "date", "home_team", "away_team",
        "home_score", "away_score", "tournament", "neutral",
    ]
    return df[cols].reset_index(drop=True)


def _read_cache() -> Optional[pd.DataFrame]:
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        return _clean(pd.read_csv(CACHE_PATH))
    except Exception:
        return None


async def fetch_results(
    session: Optional[aiohttp.ClientSession] = None,
    ttl_seconds: int = DEFAULT_TTL,
    force: bool = False,
) -> pd.DataFrame:
    """
    Return cleaned historical results as a DataFrame.

    Uses the on-disk cache when fresh; otherwise downloads, refreshes the cache,
    and falls back to the stale cache (or raises) if the network is unavailable.
    """
    fresh = (
        os.path.exists(CACHE_PATH)
        and (time.time() - os.path.getmtime(CACHE_PATH)) < ttl_seconds
    )
    if fresh and not force:
        cached = _read_cache()
        if cached is not None:
            return cached

    close = session is None
    if close:
        session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 WC-Simulator/1.0"}
        )
    try:
        async with session.get(
            RESULTS_URL, timeout=aiohttp.ClientTimeout(total=40)
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()
    except Exception:
        cached = _read_cache()
        if cached is not None:
            return cached
        raise
    finally:
        if close:
            await session.close()

    raw = pd.read_csv(io.StringIO(text))
    try:
        with open(CACHE_PATH, "w") as fh:
            fh.write(text)
    except Exception:
        pass
    return _clean(raw)


def load_results_sync(path: str = CACHE_PATH) -> pd.DataFrame:
    """Synchronous read of the cached CSV — for offline fitting / backtests."""
    cached = _read_cache() if path == CACHE_PATH else _clean(pd.read_csv(path))
    if cached is None:
        raise FileNotFoundError(
            f"No cached results at {path!r}; run fetch_results() once while online."
        )
    return cached
