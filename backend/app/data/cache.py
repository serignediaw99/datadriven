"""
Simple async JSON cache backed by SQLite.
Entries expire after `ttl_seconds`.
"""

import asyncio
import json
import time
from typing import Any, Optional

import aiosqlite

DB_PATH = "cache.db"
_lock = asyncio.Lock()


async def _get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute(
        """CREATE TABLE IF NOT EXISTS cache
           (key TEXT PRIMARY KEY, value TEXT, expires_at REAL)"""
    )
    await db.commit()
    return db


async def cache_get(key: str) -> Optional[Any]:
    async with _lock:
        db = await _get_db()
        try:
            async with db.execute(
                "SELECT value, expires_at FROM cache WHERE key=?", (key,)
            ) as cur:
                row = await cur.fetchone()
            if row and row[1] > time.time():
                return json.loads(row[0])
            return None
        finally:
            await db.close()


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    async with _lock:
        db = await _get_db()
        try:
            await db.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?,?,?)",
                (key, json.dumps(value), time.time() + ttl_seconds),
            )
            await db.commit()
        finally:
            await db.close()


async def cache_invalidate(key: str) -> None:
    async with _lock:
        db = await _get_db()
        try:
            await db.execute("DELETE FROM cache WHERE key=?", (key,))
            await db.commit()
        finally:
            await db.close()
