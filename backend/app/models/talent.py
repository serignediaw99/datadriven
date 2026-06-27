"""
Squad-talent prior: nudge team strength toward squad market value.

The Dixon-Coles ratings are results-only and miss roster quality. We correct for
that by pulling each team's overall strength (alpha + beta) toward a value-implied
strength, derived by regressing the model's own strengths on log(squad value) over
the field. Because the regression is calibrated to the model's spread, the prior
only *re-ranks* teams toward where their squad value says they belong relative to
peers — high-value/under-rated sides (e.g. France) move up, results-over-performers
relative to their value (e.g. Argentina) move down — without inventing a new scale.

Mirrors app.models.market.blend_team_params (same alpha/beta-preserving mechanics),
but the calibrating signal is squad value rather than bookmaker champion odds.
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace

import numpy as np

from app.models.ratings import TeamParams

log = logging.getLogger(__name__)


def blend_talent(
    team_params: dict[str, TeamParams],
    squad_values: dict[str, float],
    w: float = 0.8,
    clip: float = 1.5,
) -> dict[str, TeamParams]:
    """Return ``TeamParams`` nudged toward squad-value-implied strength.

    ``w`` is the weight on the model (1.0 = pure model/no prior, 0.0 = pure
    value-implied strength). Strength is ``alpha + beta``; we fit
    ``strength ~ a + b*log(value)`` over the teams present in both maps, predict
    each team's value-implied strength, blend, and split the delta evenly across
    alpha/beta so the attack/defense balance is preserved. Teams without a squad
    value pass through unchanged.
    """
    if w >= 1.0:
        return team_params

    shared = [
        t for t in team_params
        if t in squad_values and squad_values[t] > 0.0
    ]
    if len(shared) < 4:
        log.info("Talent prior skipped: only %d teams with squad values", len(shared))
        return team_params

    strength = np.array([team_params[t].alpha + team_params[t].beta for t in shared])
    log_val = np.array([math.log(squad_values[t]) for t in shared])

    # Calibrate the value scale to the strength scale via least squares.
    b, a = np.polyfit(log_val, strength, 1)
    if not np.isfinite(b) or b <= 1e-6:
        log.warning("Talent prior skipped: degenerate value->strength slope (%.4g)", b)
        return team_params

    s_lo, s_hi = strength.min() - clip, strength.max() + clip
    blended = dict(team_params)
    moved = 0
    for t in shared:
        p = team_params[t]
        s_model = p.alpha + p.beta
        s_value = min(max(a + b * math.log(squad_values[t]), s_lo), s_hi)
        s_final = w * s_model + (1.0 - w) * s_value
        half = 0.5 * (s_final - s_model)
        if abs(half) > 1e-6:
            blended[t] = replace(p, alpha=p.alpha + half, beta=p.beta + half)
            moved += 1
    log.info("Talent prior applied to %d teams (w=%.2f, slope b=%.3f)", moved, w, b)
    return blended
