"""
Global tournament state singleton.

Holds:
  - Latest raw match data (from OpenFootball)
  - Elo ratings
  - Player stats
  - Cached simulation result
  - Subscribers for live SSE pushes
"""

from __future__ import annotations

import asyncio
import unicodedata
import logging
from typing import Optional

import aiohttp

from app.data.openfootball import WCMatch, fetch_matches, extract_scorers
from app.data.elo import fetch_elo_ratings, get_team_elo, FALLBACK_ELO
from app.data.fbref import fetch_player_stats, PlayerStat
from app.models.ratings import build_team_params, TeamParams
from app.simulation.engine import SimulationResult, run as run_simulation
from app.simulation.players import PlayerEntry, build_player_entries

log = logging.getLogger(__name__)

N_SIMS = 50_000


class TournamentState:
    def __init__(self) -> None:
        self.matches: list[WCMatch] = []
        self.elo_ratings: dict[str, float] = dict(FALLBACK_ELO)
        self.player_stats: list[PlayerStat] = []
        self.team_params: dict[str, TeamParams] = {}
        self.result: Optional[SimulationResult] = None
        self._last_match_hash: int = 0
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    # --- Subscriber management (for SSE) ---

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q) if hasattr(self._subscribers, "discard") else None
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def _notify(self, event: dict) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    # --- Data refresh ---

    async def refresh(self, session: Optional[aiohttp.ClientSession] = None) -> bool:
        """
        Fetch fresh data. Returns True if match state changed and sims were re-run.
        """
        close = session is None
        if close:
            session = aiohttp.ClientSession()
        try:
            async with self._lock:
                matches = await fetch_matches(session)
                new_hash = _match_hash(matches)
                if new_hash == self._last_match_hash and self.result is not None:
                    return False

                self.matches = matches
                self._last_match_hash = new_hash

                # Refresh Elo (best-effort; don't block on failure)
                try:
                    elo = await fetch_elo_ratings(session)
                    if elo:
                        self.elo_ratings = elo
                except Exception:
                    pass

                # Refresh player stats (best-effort)
                try:
                    stats = await fetch_player_stats(session)
                    if stats:
                        self.player_stats = stats
                except Exception:
                    pass

                self.team_params = build_team_params(self.elo_ratings)

                # Build player entries from match goals + ESPN assists
                scorer_tally = extract_scorers(matches)
                # Normalize names to ASCII-lowercase for fuzzy matching between
                # openfootball scorer names and ESPN player names.
                norm_to_canonical = {_normalize_name(n): n for n in scorer_tally}
                assist_tally: dict[str, int] = {}
                for s in self.player_stats:
                    if s.assists <= 0:
                        continue
                    canonical = norm_to_canonical.get(_normalize_name(s.name), s.name)
                    assist_tally[canonical] = max(assist_tally.get(canonical, 0), s.assists)
                # Build team-of-player map from match goal data (authoritative),
                # then fill in any remaining players from ESPN stats.
                team_of_player: dict[str, str] = {}
                for m in matches:
                    if m.is_played and m.group:
                        for g in m.goals1:
                            team_of_player[g.scorer] = m.team1
                        for g in m.goals2:
                            team_of_player[g.scorer] = m.team2
                # Add ESPN-only names that haven't scored a goal yet
                for s in self.player_stats:
                    if s.name not in team_of_player and s.team:
                        team_of_player[s.name] = s.team

                team_name_to_idx = _build_team_to_idx(matches)
                players = build_player_entries(
                    scorer_tally, assist_tally, team_of_player, team_name_to_idx
                )

                log.info("Running %d simulations…", N_SIMS)
                self.result = run_simulation(matches, self.team_params, players, n=N_SIMS)
                log.info("Simulations done in %.1fs", self.result.elapsed_seconds)

                self._notify({"type": "sim_update", "timestamp": self.result.timestamp})
                return True
        finally:
            if close:
                await session.close()

    async def ensure_loaded(self) -> None:
        """Run initial refresh if not yet loaded."""
        if self.result is None:
            await self.refresh()


# --- Helpers ---

def _match_hash(matches: list[WCMatch]) -> int:
    played = [(m.num, m.score1, m.score2) for m in matches if m.is_played]
    return hash(tuple(played))


def _build_team_to_idx(matches: list[WCMatch]) -> dict[str, int]:
    teams: list[str] = []
    seen: set[str] = set()
    groups: dict[str, list[str]] = {}
    for m in matches:
        if m.group:
            groups.setdefault(m.group, [])
            for t in (m.team1, m.team2):
                if t not in groups[m.group]:
                    groups[m.group].append(t)
    for g in sorted(groups):
        for t in sorted(groups[g]):
            if t not in seen:
                teams.append(t)
                seen.add(t)
    return {t: i for i, t in enumerate(teams)}



# --- Helpers ---

def _normalize_name(name: str) -> str:
    """Fold accents and case for fuzzy player name matching."""
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()


# Module-level singleton
state = TournamentState()
