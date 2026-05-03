#!/usr/bin/env python3
# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Generate a 22-aircraft waypoint scenario near KAZO (holding + approach).

The goal is to look "realistic enough" for a demo:
- aircraft spawn at different times
- many fly a racetrack hold at different altitudes
- they are released to a simple final in staggered order
- an intruder crosses the final near the release window to create a developing conflict
"""

from __future__ import annotations

import argparse
import random
from dataclasses import asdict, dataclass
from math import cos, sin, radians
from pathlib import Path

import yaml

NM_TO_M = 1852.0


def _offset_lat_lon(lat: float, lon: float, east_m: float, north_m: float) -> tuple[float, float]:
    meters_per_deg_lat = 111_132.0
    meters_per_deg_lon = 111_132.0 * cos(radians(lat))
    d_lat = north_m / meters_per_deg_lat
    d_lon = east_m / meters_per_deg_lon if meters_per_deg_lon else 0.0
    return lat + d_lat, lon + d_lon


@dataclass(frozen=True)
class Waypoint:
    t_s: float
    lat: float
    lon: float
    alt_m: float
    gs_mps: float
    track_deg: float
    vs_mps: float


def _racetrack_hold(
    *,
    spawn_t: float,
    center_lat: float,
    center_lon: float,
    north_nm: float,
    west_nm: float,
    alt_m: float,
    gs_mps: float,
    end_t_s: float,
) -> list[Waypoint]:
    # Four corners of a box, flown as a racetrack-ish loop.
    p1 = _offset_lat_lon(center_lat, center_lon, east_m=-west_nm * NM_TO_M / 2.0, north_m=north_nm * NM_TO_M / 2.0)
    p2 = _offset_lat_lon(center_lat, center_lon, east_m=west_nm * NM_TO_M / 2.0, north_m=north_nm * NM_TO_M / 2.0)
    p3 = _offset_lat_lon(center_lat, center_lon, east_m=west_nm * NM_TO_M / 2.0, north_m=-north_nm * NM_TO_M / 2.0)
    p4 = _offset_lat_lon(center_lat, center_lon, east_m=-west_nm * NM_TO_M / 2.0, north_m=-north_nm * NM_TO_M / 2.0)

    # Each leg is ~60s.
    t = spawn_t
    wps: list[Waypoint] = [
        Waypoint(t_s=t, lat=p1[0], lon=p1[1], alt_m=alt_m, gs_mps=gs_mps, track_deg=90.0, vs_mps=0.0),
    ]
    while t < end_t_s:
        t += 60
        wps.append(Waypoint(t_s=t, lat=p2[0], lon=p2[1], alt_m=alt_m, gs_mps=gs_mps, track_deg=90.0, vs_mps=0.0))
        t += 60
        wps.append(Waypoint(t_s=t, lat=p3[0], lon=p3[1], alt_m=alt_m, gs_mps=gs_mps, track_deg=180.0, vs_mps=0.0))
        t += 60
        wps.append(Waypoint(t_s=t, lat=p4[0], lon=p4[1], alt_m=alt_m, gs_mps=gs_mps, track_deg=270.0, vs_mps=0.0))
        t += 60
        wps.append(Waypoint(t_s=t, lat=p1[0], lon=p1[1], alt_m=alt_m, gs_mps=gs_mps, track_deg=0.0, vs_mps=0.0))
    return wps


def _release_to_final(*, start_t: float, from_lat: float, from_lon: float, center_lat: float, center_lon: float, alt_m: float) -> list[Waypoint]:
    # Simple "turn south-east then descend" path toward the field.
    wps: list[Waypoint] = []
    wps.append(Waypoint(t_s=start_t, lat=from_lat, lon=from_lon, alt_m=alt_m, gs_mps=85.0, track_deg=140.0, vs_mps=0.0))
    # Intercept leg.
    t1 = start_t + 70
    p1 = _offset_lat_lon(center_lat, center_lon, east_m=-2.0 * NM_TO_M, north_m=2.0 * NM_TO_M)
    wps.append(Waypoint(t_s=t1, lat=p1[0], lon=p1[1], alt_m=alt_m - 700.0, gs_mps=80.0, track_deg=145.0, vs_mps=-2.2))
    # Short final.
    t2 = t1 + 70
    p2 = _offset_lat_lon(center_lat, center_lon, east_m=-0.6 * NM_TO_M, north_m=0.6 * NM_TO_M)
    wps.append(Waypoint(t_s=t2, lat=p2[0], lon=p2[1], alt_m=max(450.0, alt_m - 1500.0), gs_mps=70.0, track_deg=145.0, vs_mps=-1.6))
    return wps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="scenarios/bluesky/azo_flow_22.yml")
    parser.add_argument("--seed", type=int, default=20260428)
    parser.add_argument("--center-lat", type=float, default=42.2343889)
    parser.add_argument("--center-lon", type=float, default=-85.5515556)
    parser.add_argument("--duration-s", type=float, default=720.0)
    parser.add_argument("--dt-s", type=float, default=1.0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    center_lat = float(args.center_lat)
    center_lon = float(args.center_lon)

    aircraft = []

    # 20 arrivals with holds; only a subset are released to final in this demo
    # so that most traffic looks busy but doesn't generate constant alerts.
    duration_s = float(args.duration_s)
    for i in range(20):
        callsign = f"ARR{i+1:02d}"
        alt_m = 2200.0 + i * 800.0  # altitude stack (ensure > protected height separation)
        spawn_t = 20.0 + i * 12.0
        north_nm = 6.0 + rng.uniform(-0.6, 0.6)
        west_nm = 5.0 + rng.uniform(-0.6, 0.6)
        gs = 95.0 + rng.uniform(-8.0, 8.0)
        # Decide whether this aircraft is released; holds run until release, otherwise until end.
        release_t = None
        if i in {0, 2}:
            release_t = 220.0 if i == 0 else 500.0
        hold_end = float(release_t) if release_t is not None else duration_s
        wps = _racetrack_hold(
            spawn_t=spawn_t,
            center_lat=center_lat + 0.06,  # hold north of field
            center_lon=center_lon,
            north_nm=north_nm,
            west_nm=west_nm,
            alt_m=alt_m,
            gs_mps=gs,
            end_t_s=hold_end,
        )
        # Release only a couple of arrivals; keep the rest holding so the display is busy
        # but the alerting event is attributable.
        if release_t is not None:
            last = wps[-1]
            release_alt = alt_m
            if i == 2:
                release_alt = 2300.0  # so intercept leg lands near ~1600m
            wps.extend(
                _release_to_final(
                    start_t=float(release_t),
                    from_lat=last.lat,
                    from_lon=last.lon,
                    center_lat=center_lat,
                    center_lon=center_lon,
                    alt_m=release_alt,
                )
            )
        aircraft.append({"callsign": callsign, "icao24": callsign, "waypoints": [asdict(w) for w in wps]})

    # One intruder that crosses the final near the release window of mid-stack arrivals.
    intr_t0 = 540.0
    pL = _offset_lat_lon(center_lat, center_lon, east_m=-8.0 * NM_TO_M, north_m=1.5 * NM_TO_M)
    pR = _offset_lat_lon(center_lat, center_lon, east_m=8.0 * NM_TO_M, north_m=1.5 * NM_TO_M)
    intr_alt = 1600.0
    aircraft.append(
        {
            "callsign": "INTR",
            "icao24": "INTR",
            "waypoints": [
                asdict(Waypoint(t_s=intr_t0, lat=pL[0], lon=pL[1], alt_m=intr_alt, gs_mps=110.0, track_deg=90.0, vs_mps=0.0)),
                asdict(Waypoint(t_s=intr_t0 + 120.0, lat=pR[0], lon=pR[1], alt_m=intr_alt, gs_mps=110.0, track_deg=90.0, vs_mps=0.0)),
            ],
        }
    )

    # One departure climbing out (should not conflict due to vertical separation).
    dep_t0 = 120.0
    dep_p0 = _offset_lat_lon(center_lat, center_lon, east_m=0.0, north_m=0.0)
    dep_p1 = _offset_lat_lon(center_lat, center_lon, east_m=6.0 * NM_TO_M, north_m=6.0 * NM_TO_M)
    aircraft.append(
        {
            "callsign": "DEP1",
            "icao24": "DEP1",
            "waypoints": [
                asdict(Waypoint(t_s=dep_t0, lat=dep_p0[0], lon=dep_p0[1], alt_m=400.0, gs_mps=80.0, track_deg=45.0, vs_mps=6.0)),
                asdict(Waypoint(t_s=dep_t0 + 180.0, lat=dep_p1[0], lon=dep_p1[1], alt_m=2400.0, gs_mps=110.0, track_deg=45.0, vs_mps=4.0)),
            ],
        }
    )

    payload = {
        "dt_s": float(args.dt_s),
        "duration_s": float(args.duration_s),
        "name": "azo_flow_22",
        "description": "22-aircraft KAZO terminal flow: holding patterns + staggered releases + intruder crossing final.",
        "seed": int(args.seed),
        "aircraft": aircraft,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"wrote={out} aircraft={len(aircraft)} seed={args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
