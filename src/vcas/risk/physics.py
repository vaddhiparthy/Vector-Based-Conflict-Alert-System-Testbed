# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Deterministic kinematic risk from CPA and closure behavior."""

from __future__ import annotations

import math


def p_phys(distance_m: float, protected_radius_m: float, time_to_cpa_s: float) -> float:
    if protected_radius_m <= 0:
        return 0.0
    d_norm = distance_m / protected_radius_m

    # Distance risk is dominant; tuned for near misses vs far-clear pairs.
    distance_risk = 1.0 / (1.0 + math.exp((d_norm - 1.0) * 4.0))

    # Time-to-closest risk keeps conservative behavior for short look-ahead windows.
    t_sec = max(time_to_cpa_s, 0.0)
    time_risk = 1.0 / (1.0 + math.exp((t_sec - 120.0) / 60.0))

    # Floor at physics and keep within [0,1].
    score = min(1.0, distance_risk + 0.15 * time_risk)
    return float(max(0.0, score))
