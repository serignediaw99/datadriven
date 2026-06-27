"""
Transfermarkt national-team squad market values — a *talent* signal for the model.

The Dixon-Coles ratings are fit purely from match results, so they structurally
miss squad quality: a side with a world-class roster but mediocre recent results
(the canonical case being France) gets underrated. Squad market value is a strong,
orthogonal proxy for talent that the betting market also leans on. We fold it in as
a prior on team strength (see app.models.talent).

Source: Transfermarkt total squad market values for the 48 World Cup 2026 final
squads, June 2026 (as compiled by planetfootball.com's full 48-team ranking).
Transfermarkt has no open API and blocks automated access, so the values are stored
as a hardcoded snapshot; ``fetch_squad_values`` is a best-effort live hook that
falls back to it. Refresh the snapshot from a fresh Transfermarkt pull periodically.

Values are total squad market value per national team in EUR millions.
"""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

# Total squad market value per national team, EUR millions.
# Source: Transfermarkt WC-2026 final squads, June 2026 (planetfootball 48-team list).
# Keys MUST match the OpenFootball / team_params spellings used everywhere else.
SQUAD_VALUE_EUR_M: dict[str, float] = {
    "France": 1520.0,
    "England": 1360.0,
    "Spain": 1220.0,
    "Portugal": 1010.0,
    "Germany": 947.0,
    "Brazil": 928.2,
    "Argentina": 807.5,
    "Netherlands": 754.2,
    "Norway": 589.9,
    "Belgium": 547.5,
    "Ivory Coast": 522.1,
    "Senegal": 478.1,
    "Turkey": 473.7,
    "Morocco": 447.7,
    "Sweden": 406.08,
    "Croatia": 387.3,
    "USA": 385.6,
    "Ecuador": 368.7,
    "Uruguay": 359.3,
    "Switzerland": 332.5,
    "Colombia": 302.35,
    "Japan": 270.85,
    "Algeria": 256.9,
    "Austria": 245.2,
    "Ghana": 234.5,
    "Canada": 198.65,
    "Mexico": 191.85,
    "Czech Republic": 188.18,
    "Scotland": 170.25,
    "Paraguay": 153.65,
    "Bosnia & Herzegovina": 146.4,
    "DR Congo": 143.9,
    "South Korea": 139.05,
    "Egypt": 116.48,
    "Uzbekistan": 85.33,
    "Australia": 77.45,
    "Tunisia": 69.95,
    "Haiti": 55.9,
    "Cape Verde": 49.25,
    "South Africa": 49.25,
    "Saudi Arabia": 40.68,
    "Panama": 34.55,
    "New Zealand": 34.45,
    "Iran": 32.05,
    "Curaçao": 25.78,
    "Iraq": 21.2,
    "Jordan": 20.3,
    "Qatar": 19.93,
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
