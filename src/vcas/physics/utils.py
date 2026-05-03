# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Shared helpers for physics modules."""

from __future__ import annotations

from typing import Union
import numpy as np

from .relative import RelativeState
from .state import AircraftState


def as_relative(
    first: Union[AircraftState, RelativeState],
    second: Union[AircraftState, RelativeState],
) -> RelativeState:
    if isinstance(first, RelativeState) and isinstance(second, RelativeState):
        return second
    if isinstance(first, RelativeState) != isinstance(second, RelativeState):
        raise TypeError("both arguments must be AircraftState or both RelativeState")
    if isinstance(first, AircraftState) and isinstance(second, AircraftState):
        delta_r = second.position_m - first.position_m
        delta_v = second.velocity_mps - first.velocity_mps
        distance = float(np.linalg.norm(delta_r))
        if distance == 0.0:
            u_hat = np.zeros(3, dtype=float)
        else:
            u_hat = delta_r / distance
        return RelativeState(delta_r=delta_r, delta_v=delta_v, distance=distance, u_hat=u_hat)
    raise TypeError("unsupported input types for as_relative")
