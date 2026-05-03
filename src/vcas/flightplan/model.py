# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Flight plan model and interpolation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence, TypeAlias

import numpy as np

from ..geo.coords import EnuConverter


UtcEpochSeconds: TypeAlias = float


@dataclass(frozen=True)
class FlightWaypoint:
    """Single planned point in time."""

    lat: float
    lon: float
    alt_m: float
    eta_utc: datetime

    def eta_seconds(self) -> UtcEpochSeconds:
        return self.eta_utc.replace(tzinfo=timezone.utc).timestamp()


@dataclass(frozen=True)
class FlightPlan:
    """4D trajectory for a single callsign."""

    callsign: str
    waypoints: tuple[FlightWaypoint, ...]

    def sorted_waypoints(self) -> list[FlightWaypoint]:
        return sorted(self.waypoints, key=lambda wp: wp.eta_seconds())

    @property
    def has_path(self) -> bool:
        return len(self.waypoints) >= 2

    def position_at(self, timestamp_utc: datetime) -> np.ndarray:
        if not self.has_path:
            raise ValueError(f"plan for {self.callsign} must have at least two waypoints")

        waypoints = self.sorted_waypoints()
        request = timestamp_utc.astimezone(timezone.utc).timestamp()

        first = waypoints[0]
        last = waypoints[-1]
        if request <= first.eta_seconds():
            return np.array([first.lat, first.lon, first.alt_m], dtype=float)
        if request >= last.eta_seconds():
            return np.array([last.lat, last.lon, last.alt_m], dtype=float)

        for prev, next in zip(waypoints[:-1], waypoints[1:]):
            t0 = prev.eta_seconds()
            t1 = next.eta_seconds()
            if t0 <= request <= t1:
                if t1 == t0:
                    return np.array([next.lat, next.lon, next.alt_m], dtype=float)
                ratio = (request - t0) / (t1 - t0)
                return np.array(
                    [
                        prev.lat + (next.lat - prev.lat) * ratio,
                        prev.lon + (next.lon - prev.lon) * ratio,
                        prev.alt_m + (next.alt_m - prev.alt_m) * ratio,
                    ],
                    dtype=float,
                )

        return np.array([last.lat, last.lon, last.alt_m], dtype=float)

    def enu_position_at(self, timestamp_utc: datetime, converter: EnuConverter) -> np.ndarray:
        """Return ENU coordinates in meters at arbitrary timestamp."""

        if not self.has_path:
            raise ValueError(f"plan for {self.callsign} has no trajectory")
        lat, lon, alt = self.position_at(timestamp_utc)
        return converter.geodetic_to_enu(lat, lon, alt)

    @property
    def start_time_utc(self) -> datetime:
        if not self.waypoints:
            raise ValueError(f"plan for {self.callsign} has no waypoints")
        return self.sorted_waypoints()[0].eta_utc.astimezone(timezone.utc)

    @property
    def end_time_utc(self) -> datetime:
        if not self.waypoints:
            raise ValueError(f"plan for {self.callsign} has no waypoints")
        return self.sorted_waypoints()[-1].eta_utc.astimezone(timezone.utc)


def enu_projection(
    plans: Sequence[FlightPlan],
    *,
    converter: EnuConverter,
) -> dict[str, np.ndarray]:
    """Return latest ENU position for all plan waypoints (for snapshots)."""

    result: dict[str, np.ndarray] = {}
    for plan in plans:
        if not plan.has_path:
            continue
        last = plan.sorted_waypoints()[-1]
        result[plan.callsign] = converter.geodetic_to_enu(last.lat, last.lon, last.alt_m)
    return result
