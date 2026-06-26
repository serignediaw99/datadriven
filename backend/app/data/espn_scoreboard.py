"""
Near-real-time in-play scores and goal events from ESPN's scoreboard API.

Polled frequently (seconds) so the app can react to goals live, separate from the
slower OpenFootball poll that drives the simulation. Best-effort: returns [] on any
failure. Goal events carry no stable id, so callers dedupe by per-match goal count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

from app.data.fbref import _ESPN_TEAM_TO_CANONICAL, HEADERS

SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)


def _canon(name: str) -> str:
    return _ESPN_TEAM_TO_CANONICAL.get(name, name)


def _parse_minute(display_clock: str) -> int:
    """Elapsed minutes from a clock like "62'" or "90'+6'" (caps stoppage at 90+)."""
    m = re.match(r"\s*(\d+)", display_clock or "")
    return int(m.group(1)) if m else 0


@dataclass
class LiveGoal:
    team: str          # canonical name of the team that scored
    scorer: str
    minute: str        # e.g. "64'"
    own_goal: bool
    penalty: bool


@dataclass
class LiveMatch:
    event_id: str
    home: str
    away: str
    home_score: int
    away_score: int
    state: str         # "pre" | "in" | "post"
    status: str        # e.g. "1st Half", "Halftime", "Full Time"
    minute: int = 0    # elapsed match minutes (for the remaining-time fraction)
    goals: list[LiveGoal] = field(default_factory=list)  # chronological


async def fetch_scoreboard(
    session: Optional[aiohttp.ClientSession] = None,
) -> list[LiveMatch]:
    close = session is None
    if close:
        session = aiohttp.ClientSession(headers=HEADERS)
    try:
        async with session.get(
            SCOREBOARD_URL, timeout=aiohttp.ClientTimeout(total=12)
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
    except Exception:
        return []
    finally:
        if close:
            await session.close()
    return _parse(data)


def _parse(data: dict) -> list[LiveMatch]:
    out: list[LiveMatch] = []
    for event in data.get("events", []):
        comps = event.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        id_to_team = {c["id"]: _canon(c["team"]["displayName"]) for c in competitors}
        status = event.get("status", {})
        st = status.get("type", {})
        minute = _parse_minute(status.get("displayClock", ""))

        goals: list[LiveGoal] = []
        for det in comp.get("details", []):
            if not det.get("scoringPlay"):
                continue
            tid = str((det.get("team") or {}).get("id"))
            athletes = det.get("athletesInvolved") or []
            goals.append(LiveGoal(
                team=id_to_team.get(tid, ""),
                scorer=(athletes[0].get("displayName", "") if athletes else ""),
                minute=det.get("clock", {}).get("displayValue", ""),
                own_goal=bool(det.get("ownGoal")),
                penalty=bool(det.get("penaltyKick")),
            ))

        out.append(LiveMatch(
            event_id=str(event.get("id")),
            home=_canon(home["team"]["displayName"]),
            away=_canon(away["team"]["displayName"]),
            home_score=int(home.get("score") or 0),
            away_score=int(away.get("score") or 0),
            state=st.get("state", ""),
            status=st.get("description", ""),
            minute=minute,
            goals=goals,
        ))
    return out
