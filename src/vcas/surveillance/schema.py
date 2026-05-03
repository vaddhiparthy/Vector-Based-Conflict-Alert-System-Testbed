# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Surveillance frame schema shared by all input adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SourceMode = Literal["synthetic", "replay", "simulator"]


class SurveillanceFrame(BaseModel):
    """Canonical, versioned state frame used by vCAS."""

    timestamp_utc: datetime = Field(description="Frame timestamp in UTC")
    source: SourceMode
    callsign: str = Field(min_length=2, max_length=16)
    icao24: str
    lat: float
    lon: float
    alt_m: float
    gs_mps: float
    track_deg: float
    vs_mps: float

    model_config = {"frozen": True}

    def payload(self) -> dict[str, str | float | int]:
        return {
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "source": self.source,
            "callsign": self.callsign,
            "icao24": self.icao24,
            "lat": self.lat,
            "lon": self.lon,
            "alt_m": self.alt_m,
            "gs_mps": self.gs_mps,
            "track_deg": self.track_deg,
            "vs_mps": self.vs_mps,
        }
