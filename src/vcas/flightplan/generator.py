# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Flight-plan generators for synthetic and replay-sourced tracks."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from ..surveillance.schema import SurveillanceFrame
from .model import FlightPlan, FlightWaypoint


FlightPlanSource = Any


def _track_projection(
    lat: float,
    lon: float,
    alt_m: float,
    gs_mps: float,
    track_deg: float,
    vs_mps: float,
    start_t: datetime,
    end_t: datetime,
    interval_s: float,
) -> list[FlightWaypoint]:
    if interval_s <= 0:
        interval_s = 1.0
    duration_s = max(0.0, (end_t - start_t).total_seconds())
    samples = max(1, int(round(duration_s / interval_s)))
    waypoints: list[FlightWaypoint] = []
    meters_per_deg_lat = 111_132.0
    lat_rad = np.deg2rad(lat)
    meters_per_deg_lon = 111_132.0 * np.cos(lat_rad) if np.cos(lat_rad) != 0 else 0.0
    heading_rad = np.deg2rad(track_deg)
    v_east = gs_mps * np.sin(heading_rad)
    v_north = gs_mps * np.cos(heading_rad)

    for step in range(samples + 1):
        tick = min(duration_s, step * interval_s)
        ts = start_t + timedelta(seconds=float(tick))

        d_lat = v_north * tick / meters_per_deg_lat if meters_per_deg_lat else 0.0
        d_lon = v_east * tick / meters_per_deg_lon if meters_per_deg_lon else 0.0

        waypoints.append(
            FlightWaypoint(
                lat=lat + d_lat,
                lon=lon + d_lon,
                alt_m=alt_m + vs_mps * tick,
                eta_utc=ts,
            )
        )

    if waypoints and waypoints[-1].eta_utc < end_t:
        waypoints.append(
            FlightWaypoint(
                lat=waypoints[-1].lat,
                lon=waypoints[-1].lon,
                alt_m=waypoints[-1].alt_m,
                eta_utc=end_t,
            )
        )
    return waypoints


def synthetic_flight_plan_from_aircraft(
    definition: FlightPlanSource,
    *,
    aircraft: FlightPlanSource,
    start_t: datetime,
    interval_s: float = 30.0,
) -> FlightPlan:
    """Create a synthetic trajectory from aircraft kinematics and source duration."""

    end_t = start_t + timedelta(seconds=float(definition.duration_s))
    waypoints = _track_projection(
        lat=float(aircraft.lat),
        lon=float(aircraft.lon),
        alt_m=float(aircraft.alt_m),
        gs_mps=float(aircraft.gs_mps),
        track_deg=float(aircraft.track_deg),
        vs_mps=float(aircraft.vs_mps),
        start_t=start_t,
        end_t=end_t,
        interval_s=interval_s,
    )
    return FlightPlan(callsign=str(aircraft.callsign).strip().upper(), waypoints=tuple(waypoints))


def build_synthetic_flight_plans(
    definition: FlightPlanSource,
    *,
    start_t: datetime,
    interval_s: float = 30.0,
) -> dict[str, FlightPlan]:
    return {
        acft.callsign.upper(): synthetic_flight_plan_from_aircraft(
            definition,
            aircraft=acft,
            start_t=start_t,
            interval_s=interval_s,
        )
        for acft in definition.aircraft
    }


def derive_flight_plans_from_frames(
    frames: Iterable[SurveillanceFrame],
) -> dict[str, FlightPlan]:
    """Build coarse flight-plans from grouped recorded ADS-B/replay tracks."""

    grouped: dict[str, list[SurveillanceFrame]] = {}
    for frame in frames:
        grouped.setdefault(frame.callsign.upper(), []).append(frame)

    plans: dict[str, FlightPlan] = {}
    for callsign, aircraft_frames in grouped.items():
        if len(aircraft_frames) < 2:
            continue
        ordered = sorted(aircraft_frames, key=lambda item: item.timestamp_utc)
        sampled: list[SurveillanceFrame] = [ordered[0]]
        last = ordered[0].timestamp_utc

        for row in ordered[1:]:
            elapsed = (row.timestamp_utc - last).total_seconds()
            if elapsed >= 60.0:
                sampled.append(row)
                last = row.timestamp_utc

        if sampled[-1] is not ordered[-1]:
            sampled.append(ordered[-1])

        waypoints = [
            FlightWaypoint(
                lat=row.lat,
                lon=row.lon,
                alt_m=row.alt_m,
                eta_utc=row.timestamp_utc,
            )
            for row in sampled
        ]
        if len(waypoints) >= 2:
            plans[callsign] = FlightPlan(callsign=callsign, waypoints=tuple(waypoints))

    return plans
