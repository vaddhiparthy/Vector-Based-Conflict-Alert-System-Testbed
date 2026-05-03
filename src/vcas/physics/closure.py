# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Closing speed and relative-motion helpers."""

from __future__ import annotations

from typing import Union
import numpy as np

from .state import AircraftState
from .relative import RelativeState
from .utils import as_relative


def closing_speed(
    first: Union[AircraftState, RelativeState],
    second: Union[AircraftState, RelativeState],
) -> float:
    """Compute signed closing speed in meters per second."""
    relative = as_relative(first, second)
    if relative.distance <= 0.0:
        return 0.0
    return max(-float(np.dot(relative.delta_v, relative.u_hat)), 0.0)
