#!/usr/bin/env python3
# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Generate a deterministic complex synthetic scenario YAML.

Produces many "random-looking" aircraft plus one guaranteed head-on pair.
The output is deterministic for a given seed.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import asdict, dataclass
from math import cos, sin, radians
from pathlib import Path

import yaml


NM_TO_M = 1852.0


@dataclass(frozen=True)
class AircraftSpec:
    callsign: str
    icao24: str
    lat: float
    lon: float
    alt_m: float
    gs_mps: float
    track_deg: float
    vs_mps: float


def _offset_lat_lon(lat: float, lon: float, east_m: float, north_m: float) -> tuple[float, float]:
    meters_per_deg_lat = 111_132.0
    meters_per_deg_lon = 111_132.0 * cos(radians(lat))
    d_lat = north_m / meters_per_deg_lat
    d_lon = east_m / meters_per_deg_lon if meters_per_deg_lon else 0.0
    return lat + d_lat, lon + d_lon


def build_specs(
    *,
    seed: int,
    center_lat: float,
    center_lon: float,
    random_count: int,
    radius_nm_min: float,
    radius_nm_max: float,
) -> list[AircraftSpec]:
    rng = random.Random(seed)

    specs: list[AircraftSpec] = []

    # Guaranteed head-on pair.
    pair_alt_m = rng.uniform(1200.0, 2200.0)
    pair_gs = rng.uniform(65.0, 90.0)
    # Place them ~4.5 NM apart east/west and point at each other.
    sep_nm = 4.5
    a_lat, a_lon = _offset_lat_lon(center_lat, center_lon, east_m=-sep_nm * NM_TO_M / 2.0, north_m=0.0)
    b_lat, b_lon = _offset_lat_lon(center_lat, center_lon, east_m=sep_nm * NM_TO_M / 2.0, north_m=0.0)
    specs.append(
        AircraftSpec(
            callsign="H201",
            icao24="HC0A01",
            lat=a_lat,
            lon=a_lon,
            alt_m=pair_alt_m,
            gs_mps=pair_gs,
            track_deg=90.0,
            vs_mps=0.0,
        )
    )
    specs.append(
        AircraftSpec(
            callsign="H202",
            icao24="HC0A02",
            lat=b_lat,
            lon=b_lon,
            alt_m=pair_alt_m,
            gs_mps=pair_gs,
            track_deg=270.0,
            vs_mps=0.0,
        )
    )

    # Background traffic: "random-looking" but intentionally deconflicted.
    # Strategy:
    # - split into two altitude bands far apart (> protected height)
    # - mostly tangential tracks around the center (avoid direct closure)
    for i in range(random_count):
        callsign = f"R{1+i:03d}"
        icao24 = f"RC{i+1:05X}"[-6:]

        r_nm = rng.uniform(radius_nm_min, radius_nm_max)
        theta = rng.uniform(0.0, 360.0)
        east_m = r_nm * NM_TO_M * sin(radians(theta))
        north_m = r_nm * NM_TO_M * cos(radians(theta))
        lat, lon = _offset_lat_lon(center_lat, center_lon, east_m=east_m, north_m=north_m)

        # Deconflict background traffic purely by vertical separation:
        # make every background aircraft sit in a unique altitude "lane" such that
        # dz between any two background aircraft exceeds the protected height.
        alt_m = 5000.0 + (i * 800.0)

        gs_mps = rng.uniform(55.0, 115.0)

        # Tangential heading: roughly perpendicular to radial vector.
        # theta is the bearing from center to initial position; tangential is theta +/- 90.
        track_deg = (theta + (90.0 if (i % 3) else -90.0) + rng.uniform(-12.0, 12.0)) % 360.0

        vs_mps = 0.0

        specs.append(
            AircraftSpec(
                callsign=callsign,
                icao24=icao24,
                lat=lat,
                lon=lon,
                alt_m=alt_m,
                gs_mps=gs_mps,
                track_deg=track_deg,
                vs_mps=vs_mps,
            )
        )

    return specs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="scenarios/canonical/complex_traffic.yml")
    parser.add_argument("--seed", type=int, default=20260428)
    parser.add_argument("--center-lat", type=float, default=42.2343889)
    parser.add_argument("--center-lon", type=float, default=-85.5515556)
    parser.add_argument("--random-count", type=int, default=26)
    parser.add_argument("--radius-nm-min", type=float, default=2.5)
    parser.add_argument("--radius-nm-max", type=float, default=7.5)
    parser.add_argument("--duration-s", type=float, default=220.0)
    parser.add_argument("--dt-s", type=float, default=1.0)
    args = parser.parse_args()

    specs = build_specs(
        seed=args.seed,
        center_lat=args.center_lat,
        center_lon=args.center_lon,
        random_count=args.random_count,
        radius_nm_min=args.radius_nm_min,
        radius_nm_max=args.radius_nm_max,
    )

    payload = {
        "name": "complex_traffic",
        "description": "Deterministic complex traffic: many aircraft + one head-on pair (H201/H202).",
        "seed": int(args.seed),
        "aircraft": [asdict(s) for s in specs],
        "duration_s": float(args.duration_s),
        "dt_s": float(args.dt_s),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"wrote={out_path} aircraft={len(specs)} seed={args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
