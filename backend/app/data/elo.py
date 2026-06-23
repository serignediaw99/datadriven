"""
Elo ratings for the 48 WC 2026 teams.

Primary: scrape eloratings.net
Fallback: hardcoded values from June 2026 snapshot.
"""

import asyncio
import re
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

ELO_URL = "https://www.eloratings.net/World"

# Name normalisation: OpenFootball name → eloratings.net variation
_NAME_MAP: dict[str, str] = {
    "Bosnia & Herzegovina": "Bosnia-Herzegovina",
    "DR Congo": "DR Congo",
    "Cape Verde": "Cape Verde",
    "Ivory Coast": "Ivory Coast",
    "South Korea": "South Korea",
    "Czech Republic": "Czech Republic",
    "New Zealand": "New Zealand",
    "Saudi Arabia": "Saudi Arabia",
    "South Africa": "South Africa",
    "USA": "United States",
}

# Hardcoded June-2026 snapshot (used if scrape fails).
# Source: eloratings.net top-48 national teams competing in WC 2026.
FALLBACK_ELO: dict[str, float] = {
    "Spain": 2129,
    "Argentina": 2128,
    "France": 2084,
    "England": 2059,
    "Brazil": 2058,
    "Portugal": 2054,
    "Netherlands": 2042,
    "Belgium": 2032,
    "Germany": 2028,
    "Croatia": 2010,
    "Morocco": 1999,
    "Uruguay": 1988,
    "Colombia": 1980,
    "USA": 1975,
    "Mexico": 1970,
    "Switzerland": 1965,
    "Senegal": 1955,
    "Japan": 1950,
    "Ecuador": 1945,
    "Turkey": 1940,
    "Australia": 1930,
    "Canada": 1925,
    "Norway": 1920,
    "Sweden": 1915,
    "South Korea": 1905,
    "Austria": 1900,
    "Iran": 1895,
    "Egypt": 1885,
    "Algeria": 1880,
    "Paraguay": 1875,
    "Czech Republic": 1870,
    "Ivory Coast": 1865,
    "Scotland": 1860,
    "Tunisia": 1850,
    "Serbia": 1848,
    "Panama": 1840,
    "Ghana": 1835,
    "DR Congo": 1830,
    "Iraq": 1820,
    "Jordan": 1810,
    "Saudi Arabia": 1800,
    "Qatar": 1790,
    "Bosnia & Herzegovina": 1788,
    "Uzbekistan": 1780,
    "Cape Verde": 1775,
    "Haiti": 1745,
    "New Zealand": 1740,
    "South Africa": 1735,
    "Curaçao": 1720,
}


def _normalise(name: str) -> str:
    return _NAME_MAP.get(name, name).lower().strip()


async def fetch_elo_ratings(
    session: Optional[aiohttp.ClientSession] = None,
) -> dict[str, float]:
    """Return {team_name (OpenFootball spelling): elo_rating}."""
    close = session is None
    if close:
        session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 WC-Simulator/1.0"}
        )
    try:
        async with session.get(ELO_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                return FALLBACK_ELO.copy()
            html = await resp.text()
    except Exception:
        return FALLBACK_ELO.copy()
    finally:
        if close:
            await session.close()

    try:
        return _parse_elo_page(html)
    except Exception:
        return FALLBACK_ELO.copy()


def _parse_elo_page(html: str) -> dict[str, float]:
    soup = BeautifulSoup(html, "lxml")
    ratings: dict[str, float] = {}

    # eloratings.net table rows: rank | name | elo | ...
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        name_cell = cells[1].get_text(strip=True)
        elo_cell = cells[2].get_text(strip=True)
        try:
            elo = float(re.sub(r"[^\d.]", "", elo_cell))
        except ValueError:
            continue
        if name_cell and elo:
            ratings[name_cell] = elo

    # Map back to OpenFootball spelling
    reverse_map = {v.lower(): k for k, v in _NAME_MAP.items()}
    result: dict[str, float] = {}
    for name, elo in ratings.items():
        mapped = reverse_map.get(name.lower(), name)
        result[mapped] = elo

    return result if result else FALLBACK_ELO.copy()


def get_team_elo(ratings: dict[str, float], team: str) -> float:
    """Look up Elo with a graceful fallback to the average."""
    if team in ratings:
        return ratings[team]
    # Try case-insensitive
    lower = {k.lower(): v for k, v in ratings.items()}
    if team.lower() in lower:
        return lower[team.lower()]
    avg = sum(ratings.values()) / len(ratings) if ratings else 1900.0
    return avg
