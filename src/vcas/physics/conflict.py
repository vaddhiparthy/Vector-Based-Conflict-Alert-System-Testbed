# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Conflict-time utility functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union
import math
import numpy as np

from .state import AircraftState
from .relative import RelativeState
from .closure import closing_speed
from .cpa import time_to_cpa
from .utils import as_relative


@dataclass(frozen=True)
class ConflictEstimate:
    """Deterministic conflict-time estimate."""

    time_to_conflict_s: float
    closing_speed_mps: float


def time_to_conflict(
    first: Union[AircraftState, RelativeState],
    second: Union[AircraftState, RelativeState],
    protected_radius_m: float,
) -> ConflictEstimate:
    """Compute first-conflict time estimate for horizontal-only criterion."""
    rel = as_relative(first, second)
    if rel.distance <= protected_radius_m:
        return ConflictEstimate(time_to_conflict_s=0.0, closing_speed_mps=closing_speed(first, second))
    v_cl = closing_speed(first, second)
    if v_cl <= 0.0:
        return ConflictEstimate(time_to_conflict_s=math.inf, closing_speed_mps=v_cl)
    estimate = (rel.distance - protected_radius_m) / v_cl
    return ConflictEstimate(time_to_conflict_s=max(0.0, estimate), closing_speed_mps=v_cl)


@dataclass(frozen=True)
class LossResult:
    is_loss: bool
    t_min_s: float
    d_min_m: float


def loss_of_separation(
    first: Union[AircraftState, RelativeState],
    second: Union[AircraftState, RelativeState],
    protected_radius_m: float,
    protected_height_m: float,
    horizon_s: float,
) -> LossResult:
    rel = as_relative(first, second)
    t_min = time_to_cpa(first, second)
    if t_min == math.inf:
        d_min = rel.distance
    else:
        t = min(max(t_min, 0.0), max(horizon_s, 0.0))
        d_min = float(np.linalg.norm(rel.delta_r + rel.delta_v * t))
    is_violated = d_min <= protected_radius_m and abs(rel.delta_v[2] * t_min) <= protected_height_m
    return LossResult(is_loss=is_violated, t_min_s=t_min if t_min != math.inf else 0.0, d_min_m=d_min)
