# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Relative-state helper functions."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from .state import AircraftState


@dataclass(frozen=True)
class RelativeState:
    delta_r: np.ndarray
    delta_v: np.ndarray
    distance: float
    u_hat: np.ndarray


def relative_state(first: AircraftState, second: AircraftState) -> RelativeState:
    delta_r = second.position_m - first.position_m
    delta_v = second.velocity_mps - first.velocity_mps
    distance = float(np.linalg.norm(delta_r))
    if distance <= 0.0:
        u_hat = np.zeros(3, dtype=float)
    else:
        u_hat = delta_r / distance
    return RelativeState(delta_r=delta_r, delta_v=delta_v, distance=distance, u_hat=u_hat)
