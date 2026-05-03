# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Separation primitives used by risk and thread logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union
import numpy as np

from .state import AircraftState
from .relative import RelativeState
from .cpa import time_to_cpa
from .utils import as_relative


@dataclass(frozen=True)
class SeparationResult:
    t_min: float
    d_min: float
    violates_horizontal: bool


def loss_of_separation(
    first: Union[AircraftState, RelativeState],
    second: Union[AircraftState, RelativeState],
    protected_radius_m: float,
    horizon_s: float,
) -> SeparationResult:
    """Evaluate whether two states are predicted to breach protected distance."""
    rel = as_relative(first, second)
    t = time_to_cpa(first, second)
    if not np.isfinite(t):
        d_min = rel.distance
        t_eval = 0.0
    else:
        t_eval = min(max(t, 0.0), max(horizon_s, 0.0))
        d_min = float(np.linalg.norm(rel.delta_r + rel.delta_v * t_eval))
    return SeparationResult(
        t_min=t_eval,
        d_min=d_min,
        violates_horizontal=d_min <= protected_radius_m,
    )
