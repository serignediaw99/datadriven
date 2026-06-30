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
import os
import time
from typing import Optional

import math

import aiohttp

from app.data.openfootball import WCMatch, fetch_matches, extract_scorers
from app.data.elo import fetch_elo_ratings, get_team_elo, FALLBACK_ELO
from app.data.fbref import fetch_player_stats, PlayerStat
from app.data.results_history import fetch_results
from app.data.espn_scoreboard import fetch_scoreboard
from app.data import odds_api
from app.data.transfermarkt import get_squad_values
from app.models.talent import blend_talent
from app.data.metadata import host_playing_at_home
from app.models import ratings as ratings_mod
from app.models.ratings import build_team_params, build_team_params_from_model, TeamParams
from app.models.fit_dixon_coles import fit_model, save_model, load_model, FittedModel
from app.models.market import devig_outrights, blend_team_params, h2h_by_pair, blend_match_lambdas
from app.simulation.engine import SimulationResult, run as run_simulation
from app.simulation.players import PlayerEntry, build_player_entries

log = logging.getLogger(__name__)

# Monte Carlo sims per run. Memory scales ~linearly with this; lower it on small
# instances (e.g. N_SIMS=12000 on Render's 512MB tier). Default 50k for local/large.
N_SIMS = int(os.environ.get("N_SIMS", "50000"))
MODEL_PATH = "fitted_ratings.json"
# Weight on the model when blending toward bookmaker outright odds (Phase 2).
# 1.0 = pure model, 0.0 = pure market strength. Opt-in via the ODDS_API_KEY env var.
ODDS_BLEND_W = 0.7
# Weight on the model when folding in the Transfermarkt squad-talent prior (Phase 3).
# 1.0 = pure (results-only) model, 0.0 = pure squad-value strength. Applied to the
# base ratings before any odds blend so it corrects the results-only blind spot.
TALENT_BLEND_W = float(os.environ.get("TALENT_BLEND_W", "0.8"))
# Weight on the model for the per-match h2h blend. The bookmaker match market is far
# better informed than our simple model for a single game, so for now we use it
# straight (pure market for priced fixtures). Raise above 0 once the model improves.
ODDS_H2H_MODEL_W = 0.0


class TournamentState:
    def __init__(self) -> None:
        self.matches: list[WCMatch] = []
        self.elo_ratings: dict[str, float] = dict(FALLBACK_ELO)
        self.player_stats: list[PlayerStat] = []
        self.team_params: dict[str, TeamParams] = {}
        # Bookmaker h2h-derived goal-rate overrides {match.num: (lam_t1, lam_t2)} for
        # priced upcoming fixtures. Reused by the scenario endpoint so what-if sims
        # keep the same market calibration as the main one.
        self.match_overrides: dict[int, tuple[float, float]] = {}
        self.fitted_model: Optional[FittedModel] = None
        self.players: list[PlayerEntry] = []
        self.result: Optional[SimulationResult] = None
        self._last_match_hash: int = 0
        self._live_goal_counts: dict[str, int] = {}  # ESPN event id -> goals seen
        # Live in-play overlay {match.num: (cur_team1, cur_team2, fraction_remaining)};
        # fixes the current score and samples only the rest of the match.
        self.live_overlay: dict[int, tuple[int, int, float]] = {}
        # Live display state for the matches/path UI {match.num: {score1, score2,
        # state, status, minute}} (data orientation). Sourced from ESPN ahead of the
        # slower OpenFootball feed.
        self.live_status: dict[int, dict] = {}
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

    def _run_sim(self, matches=None, with_overrides: bool = True):
        """Run the simulation with the current ratings, bookmaker h2h overrides, and
        live in-play overlay applied. ``with_overrides=False`` omits the h2h blend
        (used for the pre-blend base sim)."""
        return run_simulation(
            self.matches if matches is None else matches,
            self.team_params, self.players, n=N_SIMS,
            match_lambda_overrides=(self.match_overrides or None) if with_overrides else None,
            inplay=self.live_overlay or None,
        )

    def _build_live_state(self, live_matches) -> tuple[dict, dict]:
        """
        Map ESPN in-play / just-finished matches onto sim match numbers. Returns:
          overlay {match.num: (cur_team1, cur_team2, fraction_remaining)} for the sim
                  (a final "post" match gets fraction 0.0 so its score is locked), and
          status  {match.num: {score1, score2, state, status, minute}} for the UI.
        Both in data orientation; only matches OpenFootball hasn't marked played yet.

        Knockout fixtures are matched too: once the group stage is over their slots
        hold real team names, so an in-progress R32+ game shows a live score. Slot
        codes still pending (e.g. "W74") simply never match an ESPN pair.
        """
        by_pair = {
            frozenset((m.team1, m.team2)): m
            for m in self.matches if not m.is_played
        }
        overlay: dict[int, tuple[int, int, float]] = {}
        status: dict[int, dict] = {}
        for lm in live_matches:
            if lm.state not in ("in", "post"):
                continue
            m = by_pair.get(frozenset((lm.home, lm.away)))
            if m is None:
                continue
            # data orientation (m.team1, m.team2)
            if lm.home == m.team1:
                c1, c2 = lm.home_score, lm.away_score
            else:
                c1, c2 = lm.away_score, lm.home_score
            if lm.state == "post":
                frac = 0.0
            else:
                # remaining share of a 90' match, floored so a 90'+ score isn't certain
                frac = min(1.0, max((90 - lm.minute) / 90.0, 0.03))
            status[m.num] = {
                "score1": c1, "score2": c2, "state": lm.state,
                "status": lm.status, "minute": lm.minute,
            }
            # The sim only folds a partial score into group fixtures; the knockout
            # bracket advances on completed-match winners, not in-play scores, so a
            # live KO game updates the displayed score but not the simulation yet.
            if m.group:
                overlay[m.num] = (c1, c2, frac)
        return overlay, status

    # --- Live in-play goal feed (ESPN scoreboard, polled every few seconds) ---

    async def poll_live(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """
        Poll ESPN's scoreboard and push a `goal` SSE event for each newly-scored goal.
        Cheap and independent of the simulation: dedupe by per-match goal count, and on
        the first sighting of a match record its count WITHOUT emitting (so we never
        replay goals that happened before the app was watching). Best-effort.
        """
        close = session is None
        if close:
            session = aiohttp.ClientSession()
        try:
            matches = await fetch_scoreboard(session)
        except Exception as e:
            log.debug("Live scoreboard poll failed: %s", e)
            return
        finally:
            if close and session is not None:
                await session.close()

        win_odds = {}
        if self.result is not None:
            win_odds = {r["team"]: r["probs"].get("Winner") for r in self.result.knockout_odds}

        for m in matches:
            cur = len(m.goals)
            prev = self._live_goal_counts.get(m.event_id)
            if prev is None:
                self._live_goal_counts[m.event_id] = cur  # first sighting — no replay
                continue
            if cur > prev:
                for g in m.goals[prev:cur]:
                    self._notify({
                        "type": "goal",
                        "home": m.home, "away": m.away,
                        "home_score": m.home_score, "away_score": m.away_score,
                        "team": g.team, "scorer": g.scorer, "minute": g.minute,
                        "own_goal": g.own_goal, "penalty": g.penalty,
                        "status": m.status,
                        "team_win_odds": win_odds.get(g.team),
                        "timestamp": time.time(),
                    })
                log.info("Live goal: %s %d-%d (%s %s)", m.home + " v " + m.away,
                         m.home_score, m.away_score, m.goals[-1].team, m.goals[-1].minute)
            self._live_goal_counts[m.event_id] = cur

        # Fold live scores into the simulation. Re-sim whenever the overlay changes —
        # which includes the clock ticking down (a lead is worth more with less time
        # left), not just goals — so live win probabilities update continuously.
        new_overlay, new_status = self._build_live_state(matches)
        self.live_status = new_status  # always current for the matches/path UI
        if new_overlay != self.live_overlay and (new_overlay or self.live_overlay):
            async with self._lock:
                self.live_overlay = new_overlay
                if self.team_params and self.result is not None:
                    self.result = self._run_sim()
                    self._notify({"type": "sim_update", "timestamp": self.result.timestamp})

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

                self._rebuild_team_params(matches)

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
                self.players = players

                log.info("Running %d simulations…", N_SIMS)
                self.result = self._run_sim(matches, with_overrides=False)
                log.info("Simulations done in %.1fs", self.result.elapsed_seconds)

                # Opt-in bookmaker-odds blend (re-sims with market-nudged ratings).
                await self._apply_odds_blend(session)

                self._notify({"type": "sim_update", "timestamp": self.result.timestamp})
                return True
        finally:
            if close:
                await session.close()

    def _finalist_names(self, matches: list[WCMatch]) -> list[str]:
        """Canonical names of the teams appearing in group-stage matches."""
        names: list[str] = []
        for m in matches:
            if m.group:
                for t in (m.team1, m.team2):
                    if t not in names:
                        names.append(t)
        return names

    def _rebuild_team_params(self, matches: list[WCMatch]) -> None:
        """
        Build team_params from the fitted Dixon-Coles model when available,
        falling back to the Elo heuristic. Also refreshes the module-level
        BASE_RATE / HOME_ADV (done inside build_team_params_from_model), then folds
        in the Transfermarkt squad-talent prior so the results-only ratings account
        for roster quality.
        """
        if self.fitted_model is not None:
            names = self._finalist_names(matches)
            params = build_team_params_from_model(self.fitted_model, names)
            # Fall back to the Elo heuristic for any finalist missing from the fit.
            missing = [n for n in names if n not in params]
            if missing:
                heuristic = build_team_params(self.elo_ratings)
                for n in missing:
                    if n in heuristic:
                        params[n] = heuristic[n]
            self.team_params = params
        else:
            self.team_params = build_team_params(self.elo_ratings)

        # Squad-talent prior (Phase 3): nudge strength toward squad market value.
        self.team_params = blend_talent(
            self.team_params, get_squad_values(), w=TALENT_BLEND_W
        )

    async def refit_ratings(self, session: Optional[aiohttp.ClientSession] = None) -> bool:
        """
        Re-scrape historical results, refit the Dixon-Coles model, persist it, and
        re-simulate. Heavy (downloads ~50k matches + fits); run on a daily schedule,
        not the 5-minute poll. Best-effort: leaves existing ratings intact on failure.
        """
        try:
            df = await fetch_results(session)
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(None, fit_model, df)
            del df  # free the ~50k-row DataFrame before the re-sim below
        except Exception as e:  # network / parse / fit failure
            log.warning("Ratings refit failed: %s", e)
            return False

        try:
            save_model(model, MODEL_PATH)
        except Exception:
            pass

        async with self._lock:
            self.fitted_model = model
            if self.matches:
                self._rebuild_team_params(self.matches)
                log.info(
                    "Refit Dixon-Coles ratings (as_of=%s, %d matches, gamma=%.3f); re-simulating…",
                    model.as_of.date(), model.n_matches, model.gamma,
                )
                self.result = self._run_sim(with_overrides=False)
                await self._apply_odds_blend(session)
                self._notify({"type": "sim_update", "timestamp": self.result.timestamp})
        return True

    async def _apply_odds_blend(
        self, session: Optional[aiohttp.ClientSession]
    ) -> None:
        """
        Fold bookmaker odds into the simulation and re-run (opt-in via the
        ODDS_API_KEY env var). Two independent blends, both best-effort:

          1. Outright winner market → rating-level nudge of every team's strength.
          2. Per-match h2h market → goal-rate overrides for priced upcoming group
             fixtures (calibrates matches the outright market can't, e.g. two
             no-hope teams). The market is far better informed than our simple model
             for a single game, so it dominates these (see ODDS_H2H_MODEL_W).

        Must be called with ``self.result`` already holding a base (pure-model) sim
        and with ``self._lock`` held. Any failure leaves the base sim untouched.
        """
        if not odds_api.enabled() or self.result is None or not self.matches:
            return
        close = session is None
        if close:
            session = aiohttp.ClientSession()
        try:
            outrights = await odds_api.fetch_outrights(session)
            h2h = await odds_api.fetch_h2h(session)
        except Exception as e:  # network / parse — keep the base sim
            log.warning("Odds blend skipped (fetch failed): %s", e)
            return
        finally:
            if close and session is not None:
                await session.close()

        # 1) Outright rating blend
        params = self.team_params
        market = devig_outrights(outrights) if outrights else {}
        if market:
            model_champ = {r["team"]: r["probs"]["Winner"] for r in self.result.knockout_odds}
            params = blend_team_params(params, model_champ, market, w=ODDS_BLEND_W)

        # 2) Per-match h2h goal-rate overrides (use the rating-blended params as base)
        overrides = self._build_h2h_overrides(self.matches, params, h2h) if h2h else {}
        self.match_overrides = overrides  # reused by the scenario endpoint

        if params is self.team_params and not overrides:
            return  # nothing to apply
        self.team_params = params
        log.info(
            "Re-simulating with odds blend (%d h2h match overrides)…", len(overrides)
        )
        self.result = self._run_sim(with_overrides=True)

    def _build_h2h_overrides(
        self, matches: list[WCMatch], team_params: dict[str, TeamParams], h2h_payload: list
    ) -> dict[int, tuple[float, float]]:
        """
        For each priced upcoming group fixture, blend the model's goal rates toward
        the de-vigged bookmaker h2h market. Returns {match.num: (lam_team1, lam_team2)}.
        """
        pairs = h2h_by_pair(h2h_payload)
        overrides: dict[int, tuple[float, float]] = {}
        for m in matches:
            if not (m.group and not m.is_played):
                continue
            game = pairs.get(frozenset((m.team1, m.team2)))
            if not game:
                continue
            p1 = team_params.get(m.team1)
            p2 = team_params.get(m.team2)
            if not (p1 and p2):
                continue
            h1 = ratings_mod.HOME_ADV if host_playing_at_home(m.team1, m.ground) else 0.0
            h2v = ratings_mod.HOME_ADV if host_playing_at_home(m.team2, m.ground) else 0.0
            model_l1 = ratings_mod.BASE_RATE * math.exp(p1.alpha - p2.beta + h1)
            model_l2 = ratings_mod.BASE_RATE * math.exp(p2.alpha - p1.beta + h2v)
            # Orient the market's win prob to m.team1.
            p_t1_win = game["p_home"] if game["home"] == m.team1 else game["p_away"]
            lam1, lam2 = blend_match_lambdas(
                model_l1, model_l2, p_t1_win, game["p_draw"], ODDS_H2H_MODEL_W
            )
            overrides[m.num] = (lam1, lam2)
        return overrides

    async def ensure_loaded(self) -> None:
        """Run initial refresh if not yet loaded."""
        if self.fitted_model is None:
            self.fitted_model = load_model(MODEL_PATH)
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
