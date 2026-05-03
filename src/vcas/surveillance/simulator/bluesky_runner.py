# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Headless BlueSky-compatible simulator adapter.

The adapter expects a simple YAML scenario layout and emits deterministic
``SurveillanceFrame`` objects at fixed timesteps. A pure-YAML path is used as a
safe fallback when an external BlueSky engine dependency is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml

from ..schema import SurveillanceFrame
from ..synthetic.generator import load_scenario, load_track_frames


@dataclass(frozen=True)
class BlueSkyScenario:
    """Container for simulator scenario files."""

    name: str
    yaml_path: str


@dataclass(frozen=True)
class _Waypoint:
    t_s: float
    lat: float
    lon: float
    alt_m: float
    gs_mps: float
    track_deg: float
    vs_mps: float


def _coerce_waypoint(raw: object, index: int) -> _Waypoint:
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid waypoint at index {index}")
    return _Waypoint(
        t_s=float(raw.get("t_s", index)),
        lat=float(raw.get("lat", 0.0)),
        lon=float(raw.get("lon", 0.0)),
        alt_m=float(raw.get("alt_m", 0.0)),
        gs_mps=float(raw.get("gs_mps", 0.0)),
        track_deg=float(raw.get("track_deg", 0.0)),
        vs_mps=float(raw.get("vs_mps", 0.0)),
    )


def _interpolate_waypoints(
    waypoints: list[_Waypoint],
    tick_s: float,
) -> tuple[float, float, float, float, float, float]:
    if not waypoints:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    if tick_s <= waypoints[0].t_s:
        current = waypoints[0]
        return current.lat, current.lon, current.alt_m, current.gs_mps, current.track_deg, current.vs_mps
    if tick_s >= waypoints[-1].t_s:
        end = waypoints[-1]
        return end.lat, end.lon, end.alt_m, end.gs_mps, end.track_deg, end.vs_mps

    previous = waypoints[0]
    for candidate in waypoints[1:]:
        if tick_s <= candidate.t_s:
            span_s = max(candidate.t_s - previous.t_s, 1e-6)
            ratio = (tick_s - previous.t_s) / span_s
            return (
                previous.lat + (candidate.lat - previous.lat) * ratio,
                previous.lon + (candidate.lon - previous.lon) * ratio,
                previous.alt_m + (candidate.alt_m - previous.alt_m) * ratio,
                previous.gs_mps + (candidate.gs_mps - previous.gs_mps) * ratio,
                previous.track_deg + (candidate.track_deg - previous.track_deg) * ratio,
                previous.vs_mps + (candidate.vs_mps - previous.vs_mps) * ratio,
            )
        previous = candidate

    tail = waypoints[-1]
    return tail.lat, tail.lon, tail.alt_m, tail.gs_mps, tail.track_deg, tail.vs_mps


def _waypoint_frames(aircraft: dict, dt_s: float, scenario_start: datetime) -> Iterable[tuple[datetime, SurveillanceFrame]]:
    callsign = str(aircraft.get("callsign", "SIM"))
    icao24 = str(aircraft.get("icao24", callsign))
    waypoints = [_coerce_waypoint(item, index) for index, item in enumerate(aircraft.get("waypoints", []))]
    if len(waypoints) < 2:
        raise ValueError(f"aircraft {callsign} requires at least two waypoints")

    # If the first waypoint begins after t=0, treat that as a spawn time and emit no frames before it.
    spawn_t_s = float(waypoints[0].t_s)
    duration = waypoints[-1].t_s
    step_count = max(1, int(round(duration / dt_s)))
    for tick in range(step_count + 1):
        tick_s = tick * dt_s
        if tick_s < spawn_t_s:
            continue
        timestamp = scenario_start + timedelta(seconds=tick_s)
        lat, lon, alt_m, gs_mps, track_deg, vs_mps = _interpolate_waypoints(waypoints, tick_s)
        yield (
            timestamp,
            SurveillanceFrame(
                timestamp_utc=timestamp,
                source="simulator",
                callsign=callsign,
                icao24=icao24,
                lat=lat,
                lon=lon,
                alt_m=alt_m,
                gs_mps=gs_mps,
                track_deg=track_deg,
                vs_mps=vs_mps,
            ),
        )


class BlueSkyRunner:
    """Adapter boundary for deterministic simulator scenario playback."""

    def __init__(self, scenario: BlueSkyScenario) -> None:
        self.scenario = scenario

    def frames(self) -> Iterable[SurveillanceFrame]:
        scenario_path = Path(self.scenario.yaml_path)
        if not scenario_path.exists():
            raise FileNotFoundError(f"BlueSky scenario not found: {scenario_path}")

        raw = yaml.safe_load(scenario_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"BlueSky scenario is not a YAML mapping: {scenario_path}")

        dt_s = float(raw.get("dt_s", 1.0))
        duration_s = float(raw.get("duration_s", 60.0))
        scenario_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        step_count = max(1, int(round(duration_s / dt_s)))
        duration_ticks = [scenario_start + timedelta(seconds=tick * dt_s) for tick in range(step_count + 1)]

        if "aircraft" in raw and isinstance(raw["aircraft"], list):
            has_waypoints = False
            for aircraft in raw["aircraft"]:
                if isinstance(aircraft, dict) and isinstance(aircraft.get("waypoints"), list):
                    has_waypoints = True
                    break

            if has_waypoints:
                per_aircraft = [
                    list(_waypoint_frames(aircraft, dt_s=dt_s, scenario_start=scenario_start))
                    for aircraft in raw["aircraft"]
                    if isinstance(aircraft, dict)
                ]
                by_aircraft: list[dict[datetime, SurveillanceFrame]] = [
                    {timestamp: frame for timestamp, frame in frames} for frames in per_aircraft
                ]
                for timestamp in duration_ticks:
                    for frame_map in by_aircraft:
                        frame = frame_map.get(timestamp)
                        if frame is not None:
                            yield frame
                return

            # Reuse the shared synthetic scenario path for constant-velocity entries.
            yield from load_track_frames(load_scenario(str(scenario_path)))
            return

        raise ValueError(f"Unsupported BlueSky scenario format: {scenario_path}")
