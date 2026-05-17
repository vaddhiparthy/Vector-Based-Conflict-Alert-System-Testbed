# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Thread 1 screening loop."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ..core.state import AircraftStateEnvelope, ConflictCandidate
from ..index.grid import GridIndex, GridIndexConfig
from ..physics import min_separation, time_to_conflict
from collections import deque
from ..flightplan import FlightPlan
from ..physics.state import AircraftState
from ..observability import THREAD1_CANDIDATE_PAIRS, THREAD1_LAST_CANDIDATES, THREAD1_PROCESS_SECONDS
from ..observability import traced_span


class Thread1Worker:
    """Candidate generator from a grid neighborhood."""

    def __init__(self, *, threshold_s: float, protected_radius_m: float = 1852.0, protected_height_m: float = 609.6) -> None:
        self.threshold_s = threshold_s
        self.protected_radius_m = float(protected_radius_m)
        self.protected_height_m = float(protected_height_m)
        self._grid = GridIndex(GridIndexConfig(cell_size_m=4000.0))

    def process_states(
        self,
        states: Iterable[AircraftStateEnvelope],
        *,
        frame_timestamp_utc: datetime,
        flight_plans: dict[str, FlightPlan],
        state_histories: dict[str, deque[tuple[datetime, AircraftState]]],
    ) -> list[ConflictCandidate]:
        state_list = list(states)
        with THREAD1_PROCESS_SECONDS.time():
            with traced_span("thread1.process_states", attributes={"state.count": str(len(state_list))}):
                self._grid.clear()
                state_dict = {s.callsign: s.state for s in state_list}
                candidates: list[ConflictCandidate] = []
                for envelope in state_list:
                    self._grid.insert(envelope.state)
                now = frame_timestamp_utc
                for left, right in self._grid.candidate_pairs():
                    a = state_dict[left]
                    b = state_dict[right]
                    conflict = time_to_conflict(a, b, protected_radius_m=self.protected_radius_m)
                    history_a = tuple(state_histories.get(left, deque()))
                    history_b = tuple(state_histories.get(right, deque()))
                    tc_s = conflict.time_to_conflict_s
                    # Vertical gate based on geodetic altitude (stable across ENU conversion).
                    dz_m = abs(float(getattr(a, "alt_m", 0.0)) - float(getattr(b, "alt_m", 0.0)))
                    if tc_s is not None and 0.0 <= tc_s <= self.threshold_s and dz_m <= self.protected_height_m:
                        candidate = ConflictCandidate(
                            pair=(left, right),
                            a=a,
                            b=b,
                            created_utc=now,
                            time_to_conflict_s=tc_s,
                            min_sep_m=min_separation(a, b),
                            closing_speed_mps=conflict.closing_speed_mps,
                            flight_plan_a=flight_plans.get(left),
                            flight_plan_b=flight_plans.get(right),
                            history_a=history_a,
                            history_b=history_b,
                        )
                        candidates.append(candidate)
                for _ in candidates:
                    THREAD1_CANDIDATE_PAIRS.inc()
                THREAD1_LAST_CANDIDATES.set(len(candidates))
                return candidates
