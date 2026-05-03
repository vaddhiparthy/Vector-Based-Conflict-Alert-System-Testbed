# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Closest point of approach (CPA) computations."""

from __future__ import annotations

from typing import Union
import numpy as np
from .relative import RelativeState
from .state import AircraftState
from .utils import as_relative


def time_to_cpa(first: Union[AircraftState, RelativeState], second: Union[AircraftState, RelativeState]) -> float:
    """Return t_min in seconds where relative distance is minimized."""
    rel = as_relative(first, second)
    dv2 = float(np.dot(rel.delta_v, rel.delta_v))
    if dv2 <= 0.0:
        return float("inf")
    t = -float(np.dot(rel.delta_r, rel.delta_v)) / dv2
    return max(t, 0.0)


def min_separation(
    first: Union[AircraftState, RelativeState],
    second: Union[AircraftState, RelativeState],
) -> float:
    """Return scalar minimum separation distance (m)."""
    rel = as_relative(first, second)
    dv2 = float(np.dot(rel.delta_v, rel.delta_v))
    if dv2 <= 0.0:
        return rel.distance
    t = -float(np.dot(rel.delta_r, rel.delta_v)) / dv2
    t = max(t, 0.0)
    if not np.isfinite(t):
        return rel.distance
    pos = rel.delta_r + rel.delta_v * t
    return float(np.linalg.norm(pos))
