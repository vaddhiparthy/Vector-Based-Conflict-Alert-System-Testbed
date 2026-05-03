# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Synthetic scenario parser and deterministic frame generator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import cos, sin, radians
from pathlib import Path
from typing import Iterable, List

import yaml

from ..schema import SurveillanceFrame
from ...flightplan import FlightPlan
from ...flightplan.generator import build_synthetic_flight_plans


@dataclass(frozen=True)
class ScenarioAircraft:
    callsign: str
    icao24: str
    lat: float
    lon: float
    alt_m: float
    gs_mps: float
    track_deg: float
    vs_mps: float


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    duration_s: float
    dt_s: float
    aircraft: List[ScenarioAircraft]
    seed: int | None = None


def _track_offset(lat: float, lon: float, gs_mps: float, track_deg: float, dt_s: float) -> tuple[float, float]:
    # Convert speed in m/s at latitude scale into a tiny local approximation.
    meters_per_deg_lat = 111_132.0
    meters_per_deg_lon = 111_132.0 * cos(radians(lat))
    east_mps = gs_mps * sin(radians(track_deg))
    north_mps = gs_mps * cos(radians(track_deg))
    d_lat = north_mps * dt_s / meters_per_deg_lat
    d_lon = east_mps * dt_s / meters_per_deg_lon if meters_per_deg_lon else 0.0
    return d_lat, d_lon


def load_scenario(path: str | Path) -> ScenarioDefinition:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    aircraft_data = raw.get("aircraft") or raw.get("reference", {})
    if isinstance(aircraft_data, dict):
        aircraft_data = list(aircraft_data.values())
    if not isinstance(aircraft_data, list):
        raise ValueError("scenario must define aircraft as list or reference map")
    aircraft = [
        ScenarioAircraft(
            callsign=str(item.get("callsign", "")).strip(),
            icao24=str(item.get("icao24", "")).strip(),
            lat=float(item["lat"]),
            lon=float(item["lon"]),
            alt_m=float(item["alt_m"]),
            gs_mps=float(item["gs_mps"]),
            track_deg=float(item["track_deg"]),
            vs_mps=float(item["vs_mps"]),
        )
        for item in aircraft_data
    ]
    return ScenarioDefinition(
        name=str(raw.get("name", "scenario")),
        duration_s=float(raw.get("duration_s", 60.0)),
        dt_s=float(raw.get("dt_s", 1.0)),
        aircraft=aircraft,
        seed=raw.get("seed"),
    )


def load_track_frames(definition: ScenarioDefinition) -> Iterable[SurveillanceFrame]:
    """Yield deterministic frames for every tick."""
    step_count = max(1, int(round(definition.duration_s / definition.dt_s)))
    start_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for tick in range(step_count + 1):
        timestamp = start_t + timedelta(seconds=tick * definition.dt_s)
        for acft in definition.aircraft:
            d_lat, d_lon = _track_offset(
                acft.lat,
                acft.lon,
                acft.gs_mps,
                acft.track_deg,
                tick * definition.dt_s,
            )
            yield SurveillanceFrame(
                timestamp_utc=timestamp,
                source="synthetic",
                callsign=acft.callsign,
                icao24=acft.icao24,
                lat=acft.lat + d_lat,
                lon=acft.lon + d_lon,
                alt_m=acft.alt_m + acft.vs_mps * tick * definition.dt_s,
                gs_mps=acft.gs_mps,
                track_deg=acft.track_deg,
                vs_mps=acft.vs_mps,
            )


def build_synthetic_run(
    definition: ScenarioDefinition,
    *,
    plan_interval_s: float = 30.0,
) -> tuple[Iterable[SurveillanceFrame], dict[str, FlightPlan]]:
    """Return frames and derived synthetic flight-plans for an in-memory scenario."""

    start_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frames = load_track_frames(definition)
    plans = build_synthetic_flight_plans(definition, start_t=start_t, interval_s=plan_interval_s)
    return frames, plans
