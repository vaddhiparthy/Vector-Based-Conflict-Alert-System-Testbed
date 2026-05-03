# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Uniform-band wind model used by synthetic physics projection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import yaml


@dataclass(frozen=True)
class WindBand:
    """Constant wind in one altitude band."""

    min_alt_m: float
    max_alt_m: float
    east_mps: float
    north_mps: float
    down_mps: float

    def applies_to(self, altitude_m: float) -> bool:
        return self.min_alt_m <= altitude_m <= self.max_alt_m


@dataclass(frozen=True)
class WindProfile:
    bands: tuple[WindBand, ...]

    @classmethod
    def from_path(cls, path: str | None = None) -> "WindProfile":
        default = cls.from_data([{"min_alt_m": 0, "max_alt_m": 60000, "east_mps": 0.0, "north_mps": 0.0, "down_mps": 0.0}])
        if not path:
            return default
        source = Path(path)
        if not source.exists():
            return default
        raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        bands_raw = raw.get("bands")
        if not isinstance(bands_raw, list) or not bands_raw:
            return default
        return cls.from_data(bands_raw)

    @classmethod
    def from_data(cls, rows: Iterable[dict]) -> "WindProfile":
        bands: list[WindBand] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            min_alt = float(row.get("min_alt_m", 0.0))
            max_alt = float(row.get("max_alt_m", min_alt + 1e6))
            east = float(row.get("east_mps", 0.0))
            north = float(row.get("north_mps", 0.0))
            down = float(row.get("down_mps", 0.0))
            if max_alt < min_alt:
                continue
            bands.append(WindBand(min_alt_m=min_alt, max_alt_m=max_alt, east_mps=east, north_mps=north, down_mps=down))
        if not bands:
            bands = [WindBand(min_alt_m=0.0, max_alt_m=60000.0, east_mps=0.0, north_mps=0.0, down_mps=0.0)]
        return cls(bands=tuple(sorted(bands, key=lambda band: band.min_alt_m)))


def resolve_wind(altitude_m: float, profile: WindProfile) -> np.ndarray:
    """Resolve wind as ENU vector from altitude band lookup."""

    for band in profile.bands:
        if band.applies_to(altitude_m):
            return np.array([band.east_mps, band.north_mps, band.down_mps], dtype=float)
    # Fallback to strongest band to preserve deterministic behavior for gaps.
    if not profile.bands:
        return np.zeros(3, dtype=float)
    return np.array(
        [profile.bands[-1].east_mps, profile.bands[-1].north_mps, profile.bands[-1].down_mps],
        dtype=float,
    )
