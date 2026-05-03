# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Aircraft state representation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np


@dataclass(frozen=True)
class AircraftState:
    callsign: str
    icao24: str
    timestamp: datetime
    alt_m: float
    position_m: np.ndarray
    velocity_mps: np.ndarray

    @property
    def timestamp_utc(self) -> datetime:
        if self.timestamp.tzinfo is None:
            return self.timestamp.replace(tzinfo=timezone.utc)
        return self.timestamp.astimezone(timezone.utc)

    def normalized_callsign(self) -> str:
        return (self.callsign or "").strip().upper()

