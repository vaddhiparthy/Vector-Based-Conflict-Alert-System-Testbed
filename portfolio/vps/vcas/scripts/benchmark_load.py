# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Synthetic load benchmark for frame-rate budget checks.

This benchmark is intentionally simple and deterministic so it can run as a manual
smoke for task 6.14 (performance budget) and as a future CI guard.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import time

from vcas.config.settings import Settings
from vcas.core import VcasEngine
from vcas.surveillance.synthetic.generator import (
    ScenarioAircraft,
    ScenarioDefinition,
    load_track_frames,
)
from vcas.observability import configure_structlog, get_logger

configure_structlog()
LOGGER = get_logger("vcas.scripts.benchmark_load")


def build_bench_definition(
    *,
    aircraft_count: int,
    duration_s: int,
    dt_s: float,
    center_lat: float,
    center_lon: float,
    spacing_m: float,
) -> ScenarioDefinition:
    """Build a deterministic dense-but-spread scenario for performance testing."""
    if aircraft_count <= 0:
        raise ValueError("aircraft_count must be positive")
    if dt_s <= 0:
        raise ValueError("dt_s must be positive")
    if spacing_m <= 0:
        raise ValueError("spacing_m must be positive")

    grid = int(math.ceil(math.sqrt(aircraft_count)))
    lat_step = spacing_m / 111_132.0
    lon_step = spacing_m / (111_132.0 * math.cos(math.radians(center_lat)) if center_lat else 1.0)

    aircraft: list[ScenarioAircraft] = []
    for index in range(aircraft_count):
        row = index // grid
        col = index % grid
        aircraft.append(
            ScenarioAircraft(
                callsign=f"T-{index:04d}",
                icao24=f"ICAO{index:04d}",
                lat=center_lat + (row - grid // 2) * lat_step,
                lon=center_lon + (col - grid // 2) * lon_step,
                alt_m=1_000.0 + (index % 150),
                gs_mps=70.0 + (index % 7),
                track_deg=(index * 31) % 360,
                vs_mps=0.0,
            )
        )

    return ScenarioDefinition(
        name="bench-200-load",
        duration_s=duration_s,
        dt_s=dt_s,
        aircraft=aircraft,
    )


def run_benchmark(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    definition = build_bench_definition(
        aircraft_count=args.aircraft_count,
        duration_s=args.duration_s,
        dt_s=args.dt_s,
        center_lat=settings.aerodrome_lat,
        center_lon=settings.aerodrome_lon,
        spacing_m=args.spacing_m,
    )
    frames = list(load_track_frames(definition))
    if not frames:
        raise RuntimeError("benchmark produced no frames")

    ticks = definition.duration_s / definition.dt_s + 1
    engine = VcasEngine(settings=settings)
    start = time.perf_counter()
    alerts = asyncio.run(engine.run(frames))
    elapsed = time.perf_counter() - start

    ms_per_frame = (elapsed / ticks) * 1000
    fps = ticks / elapsed if elapsed else float("inf")
    status = "PASS" if ms_per_frame <= args.max_ms_per_frame else "FAIL"

    LOGGER.info(
        "benchmark.load",
        aircraft_count=args.aircraft_count,
        duration_s=args.duration_s,
        elapsed_s=elapsed,
        status=status,
    )

    print(
        "[benchmark] "
        f"aircraft={args.aircraft_count} duration_s={args.duration_s} "
        f"frames={len(frames)} ticks={int(ticks)} "
        f"elapsed_s={elapsed:.3f} ms_per_frame={ms_per_frame:.3f} fps={fps:.2f} "
        f"alerts={len(alerts)} status={status}"
    )

    return 0 if status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frame-rate budget benchmark")
    parser.add_argument("--aircraft-count", type=int, default=200)
    parser.add_argument("--duration-s", type=int, default=5)
    parser.add_argument("--dt-s", type=float, default=1.0)
    parser.add_argument("--spacing-m", type=float, default=1500.0)
    parser.add_argument(
        "--max-ms-per-frame",
        type=float,
        default=1000.0,
        help="Fail if frame processing exceeds this average millisecond budget",
    )
    args = parser.parse_args()
    return run_benchmark(args)


if __name__ == "__main__":
    raise SystemExit(main())
