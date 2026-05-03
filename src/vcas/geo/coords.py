# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Coordinate transforms for vCAS."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


EARTH_RADIUS_M = 6_378_137.0
E2 = 6.69437999014e-3


@dataclass(frozen=True)
class ReferencePoint:
    latitude_deg: float
    longitude_deg: float
    altitude_m: float


class EnuConverter:
    """Convert lat/lon/alt states to ENU coordinates around a reference point."""

    def __init__(self, reference: ReferencePoint):
        self.reference = reference
        lat0 = np.deg2rad(reference.latitude_deg)
        lon0 = np.deg2rad(reference.longitude_deg)
        h0 = reference.altitude_m

        self._sin_lat0 = np.sin(lat0)
        self._cos_lat0 = np.cos(lat0)
        self._sin_lon0 = np.sin(lon0)
        self._cos_lon0 = np.cos(lon0)

        self._ref_ecef = self._geodetic_to_ecef(lat0, lon0, h0)

    @staticmethod
    def _geodetic_to_ecef(latitude_rad: float, longitude_rad: float, altitude_m: float) -> np.ndarray:
        n = EARTH_RADIUS_M / np.sqrt(1.0 - E2 * (np.sin(latitude_rad) ** 2))
        x = (n + altitude_m) * np.cos(latitude_rad) * np.cos(longitude_rad)
        y = (n + altitude_m) * np.cos(latitude_rad) * np.sin(longitude_rad)
        z = ((1 - E2) * n + altitude_m) * np.sin(latitude_rad)
        return np.array([x, y, z], dtype=float)

    def geodetic_to_enu(self, lat_deg: float, lon_deg: float, alt_m: float) -> np.ndarray:
        lat_rad = np.deg2rad(lat_deg)
        lon_rad = np.deg2rad(lon_deg)

        ecef = self._geodetic_to_ecef(lat_rad, lon_rad, alt_m)
        delta = ecef - self._ref_ecef

        x = -self._sin_lon0 * delta[0] + self._cos_lon0 * delta[1]
        y = (
            -self._sin_lat0 * self._cos_lon0 * delta[0]
            - self._sin_lat0 * self._sin_lon0 * delta[1]
            + self._cos_lat0 * delta[2]
        )
        z = (
            self._cos_lat0 * self._cos_lon0 * delta[0]
            + self._cos_lat0 * self._sin_lon0 * delta[1]
            + self._sin_lat0 * delta[2]
        )
        return np.array([x, y, z], dtype=float)

    def enu_to_ecef(self, enu_m: np.ndarray | list[float] | tuple[float, float, float]) -> np.ndarray:
        enu = np.asarray(enu_m, dtype=float)
        if enu.shape != (3,):
            raise ValueError("enu must be a length-3 sequence")

        east, north, up = enu
        delta_x = (
            -self._sin_lon0 * east
            - self._sin_lat0 * self._cos_lon0 * north
            + self._cos_lat0 * self._cos_lon0 * up
        )
        delta_y = (
            self._cos_lon0 * east
            - self._sin_lat0 * self._sin_lon0 * north
            + self._cos_lat0 * self._sin_lon0 * up
        )
        delta_z = self._cos_lat0 * north + self._sin_lat0 * up
        return self._ref_ecef + np.array([delta_x, delta_y, delta_z], dtype=float)

    def ecef_to_geodetic(self, ecef_xyz: np.ndarray | list[float] | tuple[float, float, float]) -> tuple[float, float, float]:
        ecef = np.asarray(ecef_xyz, dtype=float)
        if ecef.shape != (3,):
            raise ValueError("ecef_xyz must be a length-3 sequence")

        x, y, z = ecef
        p = float(np.hypot(x, y))
        lon = np.arctan2(y, x)
        lat = np.arctan2(z, p * (1 - E2))

        for _ in range(10):
            sin_lat = np.sin(lat)
            cos_lat = np.cos(lat)
            n = EARTH_RADIUS_M / np.sqrt(1.0 - E2 * (sin_lat ** 2))
            alt = p / cos_lat - n
            lat_next = np.arctan2(z, p * (1.0 - E2 * (n / (n + alt))))
            if abs(float(lat_next - lat)) < 1e-12:
                lat = lat_next
                break
            lat = lat_next

        sin_lat = np.sin(lat)
        cos_lat = np.cos(lat)
        n = EARTH_RADIUS_M / np.sqrt(1.0 - E2 * (sin_lat ** 2))
        alt_m = p / cos_lat - n
        return float(np.rad2deg(lat)), float(np.rad2deg(lon)), float(alt_m)

    def enu_to_geodetic(self, east_m: float, north_m: float, up_m: float) -> tuple[float, float, float]:
        lat_deg, lon_deg, alt_m = self.ecef_to_geodetic(self.enu_to_ecef([east_m, north_m, up_m]))
        return lat_deg, lon_deg, alt_m
