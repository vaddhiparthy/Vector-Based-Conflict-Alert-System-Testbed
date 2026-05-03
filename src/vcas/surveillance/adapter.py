# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Source adapter selection and normalization utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..config.settings import Settings
from ..flightplan import FlightPlan
from ..flightplan.generator import derive_flight_plans_from_frames
from .schema import SurveillanceFrame
from .synthetic.generator import ScenarioDefinition, build_synthetic_run, load_scenario, load_track_frames
from .replay.opensky import OpenSkyReplaySource
from .simulator.bluesky_runner import BlueSkyRunner, BlueSkyScenario


def build_synthetic_frames(path: str) -> Iterable[SurveillanceFrame]:
    scenario: ScenarioDefinition = load_scenario(path)
    return load_track_frames(scenario)


@dataclass(frozen=True)
class PreparedRun:
    frames: Iterable[SurveillanceFrame]
    flight_plans: dict[str, FlightPlan]


def build_synthetic_prepared_run(path: str, *, plan_interval_s: float = 30.0) -> PreparedRun:
    scenario: ScenarioDefinition = load_scenario(path)
    frames, plans = build_synthetic_run(scenario, plan_interval_s=plan_interval_s)
    return PreparedRun(frames=frames, flight_plans=plans)


def build_replay_frames(airport: str, start, duration_s: int, cache_root: str = "cache/opensky") -> Iterable[SurveillanceFrame]:
    return OpenSkyReplaySource(
        airport=airport,
        start=start,
        duration_s=duration_s,
        cache_root=cache_root,
        opensky_username=Settings.from_env().opensky_username,
        opensky_password=Settings.from_env().opensky_password,
    ).frames()


def build_replay_prepared_run(
    airport: str,
    start,
    duration_s: int,
    cache_root: str = "cache/opensky",
) -> PreparedRun:
    source = OpenSkyReplaySource(
        airport=airport,
        start=start,
        duration_s=duration_s,
        cache_root=cache_root,
        opensky_username=Settings.from_env().opensky_username,
        opensky_password=Settings.from_env().opensky_password,
    )
    frames = list(source.frames())
    plans = derive_flight_plans_from_frames(frames)
    return PreparedRun(frames=frames, flight_plans=plans)


def build_simulator_frames(scenario_yaml: str) -> Iterable[SurveillanceFrame]:
    return BlueSkyRunner(BlueSkyScenario(name="default", yaml_path=scenario_yaml)).frames()


def build_prepared_frames(settings: Settings) -> PreparedRun:
    if settings.source_mode == "synthetic":
        return build_synthetic_prepared_run(settings.scenario_path, plan_interval_s=30.0)
    if settings.source_mode == "replay":
        return build_replay_prepared_run(
            airport=settings.replay_airport,
            start=settings.replay_start_utc,
            duration_s=settings.replay_duration_s,
            cache_root=settings.replay_cache_root,
        )
    if settings.source_mode == "simulator":
        return PreparedRun(frames=build_simulator_frames(settings.scenario_path), flight_plans={})
    raise ValueError(f"Unsupported source mode: {settings.source_mode}")


def build_frames(settings: Settings) -> Iterable[SurveillanceFrame]:
    return build_prepared_frames(settings).frames


def build_frames_with_plans(settings: Settings) -> PreparedRun:
    return build_prepared_frames(settings)
