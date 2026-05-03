# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.vcas.physics import AircraftState, min_separation, time_to_cpa, closing_speed


def _state_from_delta(dx: float, dy: float, dz: float, vx: float, vy: float, vz: float) -> AircraftState:
    return AircraftState(
        callsign="AA100",
        icao24="ICAO1",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        alt_m=0.0,
        position_m=np.array([dx, dy, dz], dtype=float),
        velocity_mps=np.array([vx, vy, vz], dtype=float),
    )


def test_relative_symmetry():
    a = _state_from_delta(0.0, 0.0, 0.0, 150.0, 20.0, 0.0)
    b = _state_from_delta(1000.0, 200.0, 0.0, 130.0, 15.0, 0.0)
    assert closing_speed(a, b) == pytest.approx(closing_speed(b, a))


def test_head_on_approaching():
    a = _state_from_delta(0.0, 0.0, 0.0, 100.0, 0.0, 0.0)
    b = _state_from_delta(3000.0, 0.0, 0.0, -100.0, 0.0, 0.0)
    assert closing_speed(a, b) > 0
    assert time_to_cpa(a, b) == pytest.approx(15.0)
    assert min_separation(a, b) == pytest.approx(0.0)


def test_divergent_pair_no_closing_speed():
    a = _state_from_delta(0.0, 0.0, 0.0, 100.0, 0.0, 0.0)
    b = _state_from_delta(1000.0, 0.0, 0.0, 150.0, 0.0, 0.0)
    assert closing_speed(a, b) == pytest.approx(0.0)


@given(
    st.lists(
        st.tuples(
            st.floats(-5000, 5000, allow_nan=False, allow_infinity=False),
            st.floats(-5000, 5000, allow_nan=False, allow_infinity=False),
            st.floats(-5000, 5000, allow_nan=False, allow_infinity=False),
            st.floats(-300, 300, allow_nan=False, allow_infinity=False),
            st.floats(-300, 300, allow_nan=False, allow_infinity=False),
            st.floats(-300, 300, allow_nan=False, allow_infinity=False),
        ),
        min_size=2,
        max_size=2,
    )
)
def test_t_cpa_non_negative(samples):
    s1, s2 = samples
    a = AircraftState(
        callsign="AA100",
        icao24="ICAO1",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        alt_m=0.0,
        position_m=np.array([s1[0], s1[1], s1[2]], dtype=float),
        velocity_mps=np.array([s1[3], s1[4], s1[5]], dtype=float),
    )
    b = AircraftState(
        callsign="AA200",
        icao24="ICAO2",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        alt_m=0.0,
        position_m=np.array([s2[0], s2[1], s2[2]], dtype=float),
        velocity_mps=np.array([s2[3], s2[4], s2[5]], dtype=float),
    )
    assert time_to_cpa(a, b) >= 0
    assert time_to_cpa(a, b) == time_to_cpa(b, a)
    assert min_separation(a, b) >= 0
