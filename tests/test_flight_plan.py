# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from vcas.flightplan import FlightPlan, FlightWaypoint
from vcas.flightplan.generator import derive_flight_plans_from_frames, build_synthetic_flight_plans
from vcas.geo.coords import EnuConverter, ReferencePoint
from vcas.risk.flight_path import p_fp
from vcas.surveillance.schema import SurveillanceFrame
from vcas.surveillance.synthetic.generator import ScenarioAircraft, ScenarioDefinition
from vcas.core.state import ConflictCandidate
from vcas.physics.state import AircraftState


def _base_converter() -> EnuConverter:
    return EnuConverter(ReferencePoint(latitude_deg=38.944, longitude_deg=-77.455, altitude_m=100.0))


def _state_from_enums(callsign: str, timestamp: datetime, x: float, y: float, z: float) -> AircraftState:
    return AircraftState(
        callsign=callsign,
        icao24=f"ICAO-{callsign}",
        timestamp=timestamp,
        alt_m=0.0,
        position_m=np.array([x, y, z], dtype=float),
        velocity_mps=np.zeros(3, dtype=float),
    )


def _simple_frame(timestamp: datetime, callsign: str, lat: float, lon: float, alt: float) -> SurveillanceFrame:
    return SurveillanceFrame(
        timestamp_utc=timestamp,
        source="synthetic",
        callsign=callsign,
        icao24=f"ICAO-{callsign}",
        lat=lat,
        lon=lon,
        alt_m=alt,
        gs_mps=0.0,
        track_deg=0.0,
        vs_mps=0.0,
    )


def test_synthetic_plan_generation_from_scenario():
    definition = ScenarioDefinition(
        name="mini",
        duration_s=120,
        dt_s=1,
        aircraft=[
            ScenarioAircraft("N100", "ICAO100", 38.944, -77.455, 1000.0, 50.0, 90.0, 0.0),
            ScenarioAircraft("N200", "ICAO200", 38.945, -77.456, 900.0, 50.0, 270.0, 0.0),
        ],
    )
    plans = build_synthetic_flight_plans(definition, start_t=datetime(2026, 1, 1, tzinfo=timezone.utc), interval_s=30.0)
    assert set(plans.keys()) == {"N100", "N200"}
    assert len(plans["N100"].waypoints) >= 2
    assert plans["N100"].has_path


def test_replay_derived_plans_from_frames():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frames = [
        _simple_frame(start, "AC1", 38.944, -77.455, 1000.0),
        _simple_frame(start.replace(second=30), "AC1", 38.9442, -77.454, 1000.0),
        _simple_frame(start, "AC2", 38.9441, -77.4545, 1000.0),
        _simple_frame(start.replace(second=30), "AC2", 38.9441, -77.4540, 1000.0),
    ]
    plans = derive_flight_plans_from_frames(frames)
    assert set(plans.keys()) == {"AC1", "AC2"}
    assert len(plans["AC1"].waypoints) >= 2
    assert len(plans["AC2"].waypoints) >= 2


def test_p_fp_uses_plans_and_deviation():
    converter = _base_converter()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = now.replace(minute=5)

    plan_a = FlightPlan(
        callsign="AA1",
        waypoints=(
            FlightWaypoint(lat=38.944, lon=-77.455, alt_m=1000, eta_utc=now),
            FlightWaypoint(lat=38.945, lon=-77.455, alt_m=1000, eta_utc=later),
        ),
    )
    plan_b = FlightPlan(
        callsign="AA2",
        waypoints=(
            FlightWaypoint(lat=38.944, lon=-77.4545, alt_m=1000, eta_utc=now),
            FlightWaypoint(lat=38.945, lon=-77.4545, alt_m=1000, eta_utc=later),
        ),
    )

    state_a = _state_from_enums("AA1", now, *converter.geodetic_to_enu(38.944, -77.455, 1000))
    state_b = _state_from_enums("AA2", now, *converter.geodetic_to_enu(38.944, -77.4545, 1000))

    candidate = ConflictCandidate(
        pair=("AA1", "AA2"),
        a=state_a,
        b=state_b,
        created_utc=now,
        time_to_conflict_s=10.0,
        min_sep_m=100.0,
        closing_speed_mps=0.0,
        flight_plan_a=plan_a,
        flight_plan_b=plan_b,
        history_a=((now, state_a),),
        history_b=((now, state_b),),
    )

    score, metadata = p_fp(
        candidate,
        converter=converter,
        protected_radius_m=1852.0,
        flight_plan_window_s=30,
    )
    assert 0.0 < score <= 1.0
    assert metadata["source"] == "scheduled_crossing"
    assert "rms_deviation_m" in metadata


def test_p_fp_without_plans_is_zero_risk():
    converter = _base_converter()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = _state_from_enums("AA1", now, 0.0, 0.0, 0.0)

    candidate = ConflictCandidate(
        pair=("AA1", "AA2"),
        a=state,
        b=state,
        created_utc=now,
        time_to_conflict_s=10.0,
        min_sep_m=100.0,
        closing_speed_mps=0.0,
        flight_plan_a=None,
        flight_plan_b=None,
        history_a=((now, state),),
        history_b=((now, state),),
    )

    score, metadata = p_fp(
        candidate,
        converter=converter,
        protected_radius_m=1852.0,
        flight_plan_window_s=30,
    )
    assert score == 0.0
    assert metadata["source"] == "no_flight_plan"


def test_p_fp_increasing_deviation_increases_risk():
    converter = _base_converter()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plan_time = now.replace(second=5)

    def build_plan(callsign: str, lon_offset: float) -> FlightPlan:
        return FlightPlan(
            callsign=callsign,
            waypoints=(
                FlightWaypoint(lat=38.944, lon=-77.455 + lon_offset, alt_m=1000, eta_utc=now),
                FlightWaypoint(lat=38.9445, lon=-77.455 + lon_offset, alt_m=1000, eta_utc=plan_time),
            ),
        )

    plan_a = build_plan("AA1", 0.0)
    plan_b = build_plan("AA2", 0.0005)

    state_on_plan = converter.geodetic_to_enu(38.944, -77.455, 1000)
    state_off_plan = converter.geodetic_to_enu(38.944, -77.4535, 1000)
    state_a_plan = _state_from_enums("AA1", now, *state_on_plan)
    state_b_plan = _state_from_enums("AA2", now, *state_on_plan)
    state_a_off = _state_from_enums("AA1", now, *state_off_plan)

    aligned = ConflictCandidate(
        pair=("AA1", "AA2"),
        a=state_a_plan,
        b=state_b_plan,
        created_utc=now,
        time_to_conflict_s=120.0,
        min_sep_m=300.0,
        closing_speed_mps=0.0,
        flight_plan_a=plan_a,
        flight_plan_b=plan_b,
        history_a=((now, state_a_plan),),
        history_b=((now, state_b_plan),),
    )
    off_track = ConflictCandidate(
        pair=("AA1", "AA2"),
        a=state_a_off,
        b=state_b_plan,
        created_utc=now,
        time_to_conflict_s=120.0,
        min_sep_m=300.0,
        closing_speed_mps=0.0,
        flight_plan_a=plan_a,
        flight_plan_b=plan_b,
        history_a=((now, state_a_off),),
        history_b=((now, state_b_plan),),
    )

    aligned_score, aligned_meta = p_fp(
        aligned,
        converter=converter,
        protected_radius_m=1852.0,
        flight_plan_window_s=30,
    )
    off_score, off_meta = p_fp(
        off_track,
        converter=converter,
        protected_radius_m=1852.0,
        flight_plan_window_s=30,
    )

    assert aligned_meta["source"] == "scheduled_crossing"
    assert off_meta["source"] == "scheduled_crossing"
    assert off_score >= aligned_score
    assert off_score > 0.0
