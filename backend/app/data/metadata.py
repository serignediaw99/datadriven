"""
Static team metadata for the WC-2026 simulator.

- CONFEDERATION: confederation tag for each of the 48 finalists (used for
  display and an optional confederation-strength prior in the fitter).
- HOSTS_2026 + VENUE_COUNTRY: which finals venues sit in each host nation,
  so the simulator can apply home advantage when a host plays in its own
  country (openfootball stores the venue in WCMatch.ground).

All hand-maintained; no scraping required.
"""

from __future__ import annotations

HOSTS_2026: frozenset[str] = frozenset({"USA", "Mexico", "Canada"})

# WCMatch.ground string -> host country. Source: openfootball 2026 grounds.
VENUE_COUNTRY: dict[str, str] = {
    # United States (11)
    "Dallas (Arlington)": "USA",
    "Atlanta": "USA",
    "Los Angeles (Inglewood)": "USA",
    "New York/New Jersey (East Rutherford)": "USA",
    "Boston (Foxborough)": "USA",
    "Miami (Miami Gardens)": "USA",
    "Houston": "USA",
    "San Francisco Bay Area (Santa Clara)": "USA",
    "Seattle": "USA",
    "Philadelphia": "USA",
    "Kansas City": "USA",
    # Mexico (3)
    "Mexico City": "Mexico",
    "Guadalajara (Zapopan)": "Mexico",
    "Monterrey (Guadalupe)": "Mexico",
    # Canada (2)
    "Vancouver": "Canada",
    "Toronto": "Canada",
}


def host_playing_at_home(team: str, ground: str) -> bool:
    """True if `team` is a 2026 host playing a match staged in its own country."""
    return team in HOSTS_2026 and VENUE_COUNTRY.get(ground) == team


CONFEDERATION: dict[str, str] = {
    # UEFA
    "Spain": "UEFA", "France": "UEFA", "England": "UEFA", "Portugal": "UEFA",
    "Netherlands": "UEFA", "Belgium": "UEFA", "Germany": "UEFA", "Croatia": "UEFA",
    "Switzerland": "UEFA", "Turkey": "UEFA", "Norway": "UEFA", "Sweden": "UEFA",
    "Austria": "UEFA", "Czech Republic": "UEFA", "Scotland": "UEFA", "Serbia": "UEFA",
    "Bosnia & Herzegovina": "UEFA",
    # CONMEBOL
    "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL", "Paraguay": "CONMEBOL",
    # CONCACAF
    "USA": "CONCACAF", "Mexico": "CONCACAF", "Canada": "CONCACAF",
    "Panama": "CONCACAF", "Haiti": "CONCACAF", "Curaçao": "CONCACAF",
    # CAF
    "Morocco": "CAF", "Senegal": "CAF", "Egypt": "CAF", "Algeria": "CAF",
    "Tunisia": "CAF", "Ghana": "CAF", "DR Congo": "CAF", "Ivory Coast": "CAF",
    "Cape Verde": "CAF", "South Africa": "CAF",
    # AFC
    "Japan": "AFC", "South Korea": "AFC", "Australia": "AFC", "Iran": "AFC",
    "Iraq": "AFC", "Jordan": "AFC", "Saudi Arabia": "AFC", "Qatar": "AFC",
    "Uzbekistan": "AFC",
    # OFC
    "New Zealand": "OFC",
}
