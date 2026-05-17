# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Core state objects used across thread pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ..physics.state import AircraftState
from ..flightplan import FlightPlan

ThreadState = Literal["thread1", "thread2a", "thread2b", "exit"]


@dataclass(frozen=True)
class AircraftStateEnvelope:
    callsign: str
    state: AircraftState
    source: str
    ingested_utc: datetime


@dataclass(frozen=True)
class ConflictCandidate:
    pair: tuple[str, str]
    a: AircraftState
    b: AircraftState
    created_utc: datetime
    time_to_conflict_s: float | None
    min_sep_m: float | None
    closing_speed_mps: float | None
    flight_plan_a: FlightPlan | None
    flight_plan_b: FlightPlan | None
    history_a: tuple[tuple[datetime, AircraftState], ...]
    history_b: tuple[tuple[datetime, AircraftState], ...]


@dataclass
class AlertRecord:
    alert_id: str
    pair: tuple[str, str]
    created_utc: datetime
    thread_state: ThreadState
    risk_total: float
    risk_phys: float
    risk_fp: float
    risk_ml: float
    tc_s: float
    d_min_m: float
    bucket: str
    metadata: dict
