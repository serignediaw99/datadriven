"""
Transfermarkt national-team squad market values — a *talent* signal for the model.

The Dixon-Coles ratings are fit purely from match results, so they structurally
miss squad quality: a side with a world-class roster but mediocre recent results
(the canonical case being France) gets underrated. Squad market value is a strong,
orthogonal proxy for talent that the betting market also leans on. We fold it in as
a prior on team strength (see app.models.talent).

Primary source: a maintainable hardcoded snapshot of total squad market values in
EUR millions. Transfermarkt has no open API and aggressively blocks scrapers, so —
unlike a fragile live scrape that silently serves stale data — the snapshot IS the
dependable source. ``fetch_squad_values`` is a best-effort live hook that falls back
to the snapshot; refresh the snapshot from a real Transfermarkt pull periodically.

Snapshot vintage: ~2025-26 cycle, total squad market value per national team (EUR m).
Values are approximate; the talent blend only uses their *relative* ordering and
rough magnitude (a log-value regression calibrated to the model's own spread), so
small absolute errors wash out.
"""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

# Total squad market value per national team, EUR millions (approximate snapshot).
# Keys MUST match the OpenFootball / team_params spellings used everywhere else.
SQUAD_VALUE_EUR_M: dict[str, float] = {
    # Elite European squads
    "England": 1450.0,
    "France": 1130.0,
    "Spain": 1060.0,
    "Portugal": 940.0,
    "Germany": 900.0,
    "Brazil": 800.0,
    "Netherlands": 760.0,
    "Argentina": 650.0,
    "Italy": 600.0,           # not in the field, kept for completeness/fetch parity
    "Belgium": 470.0,
    "Turkey": 380.0,
    "Croatia": 350.0,
    "Uruguay": 350.0,
    "Norway": 340.0,
    "Morocco": 320.0,
    "Austria": 300.0,
    "Colombia": 300.0,
    "Japan": 290.0,
    "Senegal": 280.0,
    "USA": 260.0,
    "Ecuador": 250.0,
    "Switzerland": 250.0,
    "Ivory Coast": 210.0,
    "Algeria": 200.0,
    "Sweden": 200.0,
    "Ghana": 180.0,
    "Scotland": 180.0,
    "South Korea": 175.0,
    "Egypt": 155.0,
    "Czech Republic": 150.0,
    "Mexico": 150.0,
    "Canada": 140.0,
    "DR Congo": 125.0,
    "Bosnia & Herzegovina": 120.0,
    "Paraguay": 90.0,
    "Cape Verde": 75.0,
    "Australia": 70.0,
    "Iran": 70.0,
    "Tunisia": 60.0,
    "South Africa": 55.0,
    "Uzbekistan": 45.0,
    "Saudi Arabia": 35.0,
    "Panama": 35.0,
    "Haiti": 35.0,
    "New Zealand": 30.0,
    "Iraq": 30.0,
    "Qatar": 30.0,
    "Jordan": 20.0,
    "Curaçao": 20.0,
}


def get_squad_values() -> dict[str, float]:
    """Return {team_name: total squad market value in EUR millions} (snapshot)."""
    return dict(SQUAD_VALUE_EUR_M)


async def fetch_squad_values(
    session: Optional[aiohttp.ClientSession] = None,
) -> dict[str, float]:
    """Best-effort live squad values; falls back to the snapshot.

    Transfermarkt blocks most automated access, so this is intentionally
    conservative: any failure (or an empty parse) returns the snapshot rather
    than degrading the model. Wire a real source in here when available.
    """
    # No reliable open endpoint today — serve the maintained snapshot. Kept async
    # and signature-compatible with the other data fetchers so a real pull can be
    # dropped in without touching callers.
    return get_squad_values()
