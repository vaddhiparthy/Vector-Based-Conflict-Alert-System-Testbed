# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Random-but-reproducible waypoint scenario generator.

This intentionally generates *synthetic* traffic for demo/testing. It is not
connected to live ADS-B sources.

Design goals:
- Many background aircraft spread out (not clustered).
- Two test aircraft (TST1/TST2) whose early motion is "benign" and only later
  converges into a conflict window.
- A seed is always recorded so the scenario is reproducible and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
from random import Random
from typing import Any


M_PER_NM = 1852.0


@dataclass(frozen=True)
class Aerodrome:
    lat: float
    lon: float
    alt_m: float = 100.0


def _offset_lat_lon(aero: Aerodrome, east_m: float, north_m: float) -> tuple[float, float]:
    # Small-angle local approximation (good enough for a 50nm demo bubble).
    meters_per_deg_lat = 111_132.0
    meters_per_deg_lon = 111_132.0 * cos(aero.lat * pi / 180.0)
    d_lat = north_m / meters_per_deg_lat
    d_lon = east_m / meters_per_deg_lon if meters_per_deg_lon else 0.0
    return aero.lat + d_lat, aero.lon + d_lon


def _pick_point(rng: Random, aero: Aerodrome, r_min_nm: float, r_max_nm: float) -> tuple[float, float]:
    r = (r_min_nm + (r_max_nm - r_min_nm) * rng.random()) * M_PER_NM
    theta = rng.random() * 2.0 * pi
    east = r * cos(theta)
    north = r * sin(theta)
    return _offset_lat_lon(aero, east, north)


def _bg_aircraft(rng: Random, idx: int, aero: Aerodrome, duration_s: int) -> dict[str, Any]:
    callsign = f"BG{idx:02d}"
    icao24 = callsign
    spawn = int(rng.random() * min(240, max(60, duration_s // 3)))
    # Give each background aircraft a unique altitude separated by > protected
    # height (default ~610m). This makes bg-bg alerts extremely unlikely even
    # if horizontal paths cross.
    alt_m = 7000 + idx * 700
    gs_mps = rng.choice([90, 105, 115, 125, 135, 145])

    # Spread out without leaving everything off-screen: keep within ~10-30nm of the field.
    # Start/end are on different sides; a mid point introduces a gentle turn.
    p0 = _pick_point(rng, aero, 10, 30)
    p2 = _pick_point(rng, aero, 10, 30)
    pm = _pick_point(rng, aero, 6, 22)

    t0 = spawn
    t1 = spawn + int(120 + rng.random() * 120)
    t2 = min(duration_s, t1 + int(160 + rng.random() * 160))

    return {
        "callsign": callsign,
        "icao24": icao24,
        "waypoints": [
            {"t_s": t0, "lat": p0[0], "lon": p0[1], "alt_m": alt_m, "gs_mps": gs_mps, "track_deg": 0, "vs_mps": 0},
            {"t_s": t1, "lat": pm[0], "lon": pm[1], "alt_m": alt_m, "gs_mps": gs_mps, "track_deg": 0, "vs_mps": 0},
            {"t_s": t2, "lat": p2[0], "lon": p2[1], "alt_m": alt_m, "gs_mps": gs_mps, "track_deg": 0, "vs_mps": 0},
        ],
    }


def _test_pair(rng: Random, aero: Aerodrome, duration_s: int) -> list[dict[str, Any]]:
    # Force a late conflict window so early frames are "benign".
    t_conflict = int(duration_s * 0.78)
    t_end = min(duration_s, t_conflict + 120)

    # Two random start regions, far apart.
    start1 = _pick_point(rng, aero, 22, 40)
    start2 = _pick_point(rng, aero, 22, 40)

    # Early midpoints keep them doing unrelated work.
    mid1 = _pick_point(rng, aero, 14, 28)
    mid2 = _pick_point(rng, aero, 14, 28)

    # Conflict corridor: pick two points near the field, slightly offset, and have them cross.
    c0 = _offset_lat_lon(aero, east_m=-4.0 * M_PER_NM, north_m=1.5 * M_PER_NM)
    c1 = _offset_lat_lon(aero, east_m=4.0 * M_PER_NM, north_m=-1.0 * M_PER_NM)

    alt = rng.choice([2100, 2200, 2300, 2400, 2600])

    t1_spawn = 0
    t2_spawn = int(30 + rng.random() * 90)

    tst1 = {
        "callsign": "TST1",
        "icao24": "TST1",
        "waypoints": [
            {"t_s": t1_spawn, "lat": start1[0], "lon": start1[1], "alt_m": alt, "gs_mps": 110, "track_deg": 0, "vs_mps": 0},
            {"t_s": int(t_conflict * 0.45), "lat": mid1[0], "lon": mid1[1], "alt_m": alt + 100, "gs_mps": 105, "track_deg": 0, "vs_mps": -0.2},
            {"t_s": t_conflict, "lat": c0[0], "lon": c0[1], "alt_m": alt, "gs_mps": 98, "track_deg": 0, "vs_mps": -0.1},
            {"t_s": t_end, "lat": c1[0], "lon": c1[1], "alt_m": alt, "gs_mps": 95, "track_deg": 0, "vs_mps": 0},
        ],
    }
    tst2 = {
        "callsign": "TST2",
        "icao24": "TST2",
        "waypoints": [
            {"t_s": t2_spawn, "lat": start2[0], "lon": start2[1], "alt_m": alt, "gs_mps": 115, "track_deg": 0, "vs_mps": 0},
            {"t_s": int(t_conflict * 0.55), "lat": mid2[0], "lon": mid2[1], "alt_m": alt - 50, "gs_mps": 110, "track_deg": 0, "vs_mps": 0.15},
            {"t_s": t_conflict, "lat": c1[0], "lon": c1[1], "alt_m": alt, "gs_mps": 100, "track_deg": 0, "vs_mps": 0},
            {"t_s": t_end, "lat": c0[0], "lon": c0[1], "alt_m": alt, "gs_mps": 98, "track_deg": 0, "vs_mps": 0},
        ],
    }
    return [tst1, tst2]


def generate_random_waypoint_scenario(
    *,
    seed: int,
    aerodrome: Aerodrome,
    bg_count: int = 18,
    duration_s: int = 600,
    dt_s: float = 1.0,
) -> dict[str, Any]:
    rng = Random(seed)
    bg_count = max(0, min(int(bg_count), 80))
    duration_s = max(120, min(int(duration_s), 1800))
    dt_s = float(dt_s) if dt_s else 1.0

    aircraft: list[dict[str, Any]] = []
    # Extra safety: spread background aircraft into distinct altitude "bands" so
    # bg-bg alerts are extremely unlikely even if paths cross.
    for i in range(1, bg_count + 1):
        aircraft.append(_bg_aircraft(rng, i, aerodrome, duration_s))
    aircraft.extend(_test_pair(rng, aerodrome, duration_s))

    return {
        "dt_s": dt_s,
        "duration_s": duration_s,
        "name": f"generated_random_{seed}",
        "description": (
            "Generated random waypoint traffic (seeded). Background aircraft are spread out; "
            "TST1/TST2 only converge late into a conflict window."
        ),
        "seed": seed,
        "reference": {"aerodrome": {"lat": aerodrome.lat, "lon": aerodrome.lon, "alt_m": aerodrome.alt_m}},
        "aircraft": aircraft,
    }
