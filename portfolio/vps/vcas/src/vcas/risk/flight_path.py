# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Flight-plan risk term derived from scheduled trajectory interaction."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

import numpy as np

from ..flightplan import FlightPlan
from ..geo.coords import EnuConverter
from ..physics.state import AircraftState

if TYPE_CHECKING:
    from ..core.state import ConflictCandidate


@dataclass(frozen=True)
class FlightPlanRisk:
    """Structured metadata for flight-plan risk outputs."""

    source: str
    min_planned_separation_m: float
    rms_deviation_m: float
    crossing_happens: bool
    forecast_horizon_s: int


def _sampled_times(start: float, end: float, *, step_s: float) -> list[float]:
    if end <= start:
        return [start]
    if step_s <= 0:
        return [start, end]
    count = int(max(2, (end - start) / step_s + 1))
    return [start + i * step_s for i in range(count) if start + i * step_s <= end]


def _interpolate_deviation(
    plan: FlightPlan,
    candidate_states: Sequence[tuple[datetime, AircraftState]],
    *,
    converter: EnuConverter,
    window_s: float,
) -> float:
    if not candidate_states:
        return 0.0

    latest_ts = candidate_states[-1][0].astimezone(timezone.utc)
    window_start = latest_ts.timestamp() - max(0.0, window_s)
    filtered = [(ts, pos) for ts, pos in candidate_states if ts.timestamp() >= window_start]
    if not filtered:
        filtered = candidate_states[-1:]

    squared_errors: list[float] = []
    for ts, actual_state in filtered:
        actual_pos = actual_state.position_m
        planned = plan.enu_position_at(ts, converter=converter)
        error = float(np.linalg.norm(actual_pos - planned))
        squared_errors.append(error * error)

    return float(np.sqrt(np.mean(squared_errors)))


def _min_planned_separation(
    a: FlightPlan,
    b: FlightPlan,
    *,
    converter: EnuConverter,
    now: datetime,
    horizon_s: int,
    step_s: int,
) -> float:
    start = now.astimezone(timezone.utc).timestamp()
    end = start + max(0, horizon_s)
    min_sep = float("inf")
    for sample in _sampled_times(start, end, step_s=float(step_s)):
        ts = datetime.fromtimestamp(sample, tz=timezone.utc)
        pos_a = a.enu_position_at(ts, converter=converter)
        pos_b = b.enu_position_at(ts, converter=converter)
        sep = float(np.linalg.norm(pos_a - pos_b))
        if sep < min_sep:
            min_sep = sep
    if np.isinf(min_sep):
        return 0.0
    return min_sep


def _sigmoid(x: float, *, scale: float = 5000.0, midpoint: float = 1.0) -> float:
    if scale == 0:
        return 1.0 if x > midpoint else 0.0
    return 1.0 / (1.0 + np.exp((x - midpoint) * scale))


def _deviation_risk(rms_error_m: float) -> float:
    # Larger lateral/vertical plan deviation should increase risk.
    # The risk profile is bounded and centered near ~400m of accumulated drift.
    return 1.0 - _sigmoid(rms_error_m, scale=0.02, midpoint=400.0)


def _planned_risk(min_sep_m: float, protected_radius_m: float) -> float:
    if protected_radius_m <= 0.0:
        return 0.0
    normalized = min_sep_m / protected_radius_m
    # deterministic ramp with hardening at near protected proximity
    # lower separation means higher risk (approaching 1 as min_sep -> 0)
    # keep deterministic shape and bounded output
    score = 1.0 / (1.0 + np.exp((normalized - 1.0) * 4.0))
    return float(max(0.0, min(1.0, score)))


def p_fp(
    candidate: "ConflictCandidate",
    *,
    converter: EnuConverter,
    protected_radius_m: float,
    flight_plan_window_s: int,
) -> tuple[float, dict[str, object]]:
    """Return flight-plan risk and metadata from scheduled trajectory analysis."""

    if candidate.flight_plan_a is None or candidate.flight_plan_b is None:
        return 0.0, {"source": "no_flight_plan"}

    now = candidate.created_utc
    # Crossing-point estimate by comparing scheduled positions in ENU over a short horizon.
    min_sep = _min_planned_separation(
        candidate.flight_plan_a,
        candidate.flight_plan_b,
        converter=converter,
        now=now,
        horizon_s=300,
        step_s=5,
    )

    # Deviation in rolling window: actual-to-plan residual norm.
    hist_a = candidate.history_a
    hist_b = candidate.history_b
    rms_a = _interpolate_deviation(
        candidate.flight_plan_a,
        hist_a,
        converter=converter,
        window_s=float(flight_plan_window_s),
    )
    rms_b = _interpolate_deviation(
        candidate.flight_plan_b,
        hist_b,
        converter=converter,
        window_s=float(flight_plan_window_s),
    )
    rms = max(rms_a, rms_b)

    risk_planned = _planned_risk(min_sep, protected_radius_m=protected_radius_m)
    risk_deviation = _deviation_risk(rms)
    total = float(max(0.0, min(1.0, 0.65 * risk_planned + 0.35 * risk_deviation)))

    crossing_happens = min_sep <= protected_radius_m * 2.0
    return total, {
        "source": "scheduled_crossing",
        "min_planned_separation_m": float(min_sep),
        "rms_deviation_m": float(rms),
        "crossing_happens": bool(crossing_happens),
        "forecast_horizon_s": 300,
    }


def deviation_score_from_history(
    state_a: np.ndarray,
    plan_a: FlightPlan,
    state_b: np.ndarray,
    plan_b: FlightPlan,
    now: datetime,
    *,
    converter: EnuConverter,
    window_s: float,
) -> float:
    """Return a pair-level deviation score from two instantaneous positions."""

    rms_a = float(np.linalg.norm(state_a - plan_a.enu_position_at(now, converter=converter)))
    rms_b = float(np.linalg.norm(state_b - plan_b.enu_position_at(now, converter=converter)))
    return float(max(rms_a, rms_b)) * 0.35


__all__ = [
    "FlightPlanRisk",
    "p_fp",
    "deviation_score_from_history",
]
