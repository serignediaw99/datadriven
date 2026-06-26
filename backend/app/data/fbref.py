"""
Fetch player goal + assist data from the ESPN World Cup statistics API.

Falls back gracefully to an empty list if the request fails.
"""

import re
from dataclasses import dataclass
from typing import Optional

import aiohttp

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/statistics?limit=100"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

_G_RE = re.compile(r'G:\s*(\d+)')
_A_RE = re.compile(r'A:\s*(\d+)')
_M_RE = re.compile(r'M:\s*(\d+)')

# ESPN team names that differ from the simulator's canonical names.
_ESPN_TEAM_TO_CANONICAL = {
    "United States": "USA",
    "Congo DR": "DR Congo",
    "Czechia": "Czech Republic",
    "Bosnia-Herzegovina": "Bosnia & Herzegovina",
    "Türkiye": "Turkey",
}


def _espn_team(athlete: dict) -> str:
    name = (athlete.get("team") or {}).get("name", "").strip()
    return _ESPN_TEAM_TO_CANONICAL.get(name, name)


@dataclass
class PlayerStat:
    name: str
    team: str          # canonical national-team name from ESPN (athlete.team.name)
    goals: int
    assists: int
    matches_played: int
    minutes: int


async def fetch_player_stats(
    session: Optional[aiohttp.ClientSession] = None,
) -> list[PlayerStat]:
    close = session is None
    if close:
        session = aiohttp.ClientSession(headers=HEADERS)
    try:
        async with session.get(
            ESPN_URL, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
    except Exception:
        return []
    finally:
        if close:
            await session.close()

    return _parse_espn(data)


def _parse_espn(data: dict) -> list[PlayerStat]:
    seen: dict[str, PlayerStat] = {}

    for category in data.get("stats", []):
        for entry in category.get("leaders", []):
            athlete = entry.get("athlete", {})
            name = athlete.get("displayName", "").strip()
            if not name:
                continue
            team = _espn_team(athlete)
            sv = entry.get("shortDisplayValue", "")
            g_m = _G_RE.search(sv)
            a_m = _A_RE.search(sv)
            m_m = _M_RE.search(sv)
            goals   = int(g_m.group(1)) if g_m else 0
            assists = int(a_m.group(1)) if a_m else 0
            mp      = int(m_m.group(1)) if m_m else 0

            if name in seen:
                # Merge: take max of each stat across categories (keep known team)
                existing = seen[name]
                seen[name] = PlayerStat(
                    name=name, team=team or existing.team,
                    goals=max(existing.goals, goals),
                    assists=max(existing.assists, assists),
                    matches_played=max(existing.matches_played, mp),
                    minutes=0,
                )
            else:
                seen[name] = PlayerStat(
                    name=name, team=team,
                    goals=goals, assists=assists,
                    matches_played=mp, minutes=0,
                )

    return sorted(seen.values(), key=lambda s: (-s.goals, -s.assists))
