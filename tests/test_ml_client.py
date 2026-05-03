# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

import asyncio
from datetime import datetime

import numpy as np

from vcas.core.state import ConflictCandidate
from vcas.physics.state import AircraftState
from vcas.risk.ml_client import build_feature_matrix, p_ml


def _state(ts: float, *, callsign: str, icao24: str, x: float, y: float, z: float) -> AircraftState:
    return AircraftState(
        callsign=callsign,
        icao24=icao24,
        timestamp=datetime.fromtimestamp(ts),
        alt_m=0.0,
        position_m=np.array([x, y, z], dtype=float),
        velocity_mps=np.array([1.0, 0.0, 0.0], dtype=float),
    )


def test_build_feature_matrix_uses_history_pairing() -> None:
    candidate = ConflictCandidate(
        pair=("A", "B"),
        a=_state(0, callsign="A", icao24="A1", x=0, y=0, z=0),
        b=_state(0, callsign="B", icao24="B1", x=10, y=0, z=0),
        created_utc=datetime.fromtimestamp(0),
        time_to_conflict_s=60.0,
        min_sep_m=10.0,
        closing_speed_mps=1.0,
        flight_plan_a=None,
        flight_plan_b=None,
        history_a=((datetime.fromtimestamp(0), _state(0, callsign="A", icao24="A1", x=0, y=0, z=0)),),
        history_b=((datetime.fromtimestamp(0), _state(0, callsign="B", icao24="B1", x=10, y=0, z=0)),),
    )
    features = build_feature_matrix(candidate, sample_count=1)
    assert features.shape == (1, 6)
    assert features[0][0] == 10.0
    assert features[0][1] == 0.0


def test_p_ml_fallback_when_disabled() -> None:
    values = np.array([[1000.0, 0.0, 0.0, 1.0, 90.0, 60.0]], dtype=float)
    assert np.allclose(asyncio.run(p_ml(values, service_healthy=False)), [0.0])
