#!/usr/bin/env python3
"""Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.

All rights reserved.

Non-commercial use is permitted for review and research only.

Fetch an OpenSky historical window and write it to the deterministic replay cache.

This script is optional and requires:
- OpenSky credentials in env (`VCAS_OPENSKY_USERNAME`, `VCAS_OPENSKY_PASSWORD`)
- `pyopensky` installed in the active environment

It writes line-delimited JSON (one SurveillanceFrame per line) into:
  cache/opensky/<AIRPORT>_<START_UNIX>_<DURATION_S>.yaml
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from vcas.config.settings import Settings
from vcas.surveillance.replay.opensky import OpenSkyReplaySource


def _parse_iso(value: str) -> datetime:
    # Accept "2026-01-01T00:00:00Z" and naive strings (treated as UTC).
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--airport", required=True, help="Airport ICAO (e.g., LFBO)")
    parser.add_argument("--start-utc", required=True, help="ISO timestamp (e.g., 2026-01-01T00:00:00Z)")
    parser.add_argument("--duration-s", type=int, default=3600, help="Window duration in seconds")
    parser.add_argument("--cache-root", default="cache/opensky", help="Cache root directory")
    parser.add_argument("--bbox-pad-deg", type=float, default=1.0, help="Bounding box padding degrees around aerodrome")
    args = parser.parse_args()

    settings = Settings.from_env()
    if not settings.opensky_username or not settings.opensky_password:
        raise SystemExit("Missing OpenSky credentials in env (VCAS_OPENSKY_USERNAME/VCAS_OPENSKY_PASSWORD).")

    start = _parse_iso(args.start_utc)
    source = OpenSkyReplaySource(
        airport=args.airport,
        start=start,
        duration_s=int(args.duration_s),
        cache_root=str(args.cache_root),
        opensky_username=settings.opensky_username,
        opensky_password=settings.opensky_password,
        bbox_pad_deg=float(args.bbox_pad_deg),
    )
    frames = list(source._fetch_frames_pyopensky())
    if not frames:
        raise SystemExit("OpenSky query returned 0 frames; check bbox/time window and credentials.")

    source.cache_window(frames)
    print(f"cached_frames={len(frames)} path={source.cache_path()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
