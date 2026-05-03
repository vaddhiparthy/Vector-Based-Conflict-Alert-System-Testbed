# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""OpenSky replay adapter with deterministic local cache fallback.

This adapter supports two paths:
1) Cache-only: replay a previously cached OpenSky window from disk (deterministic).
2) Fetch-to-cache: when OpenSky credentials are present and `pyopensky` is installed,
   fetch a window from OpenSky and write the same cache format to disk for future
   deterministic replays.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from ..schema import SurveillanceFrame


class OpenSkyReplaySource:
    """Load cached scenario-like rows or fail gracefully when not configured."""

    def __init__(
        self,
        *,
        airport: str,
        start: datetime,
        duration_s: int,
        cache_root: str = "cache/opensky",
        opensky_username: str = "",
        opensky_password: str = "",
        bbox_pad_deg: float = 1.0,
    ) -> None:
        self.airport = airport
        self.start = start
        self.duration_s = duration_s
        self.cache_root = Path(cache_root)
        self.opensky_username = opensky_username
        self.opensky_password = opensky_password
        self.bbox_pad_deg = float(bbox_pad_deg)

    def cache_path(self) -> Path:
        return self.cache_root / f"{self.airport}_{int(self.start.timestamp())}_{self.duration_s}.yaml"

    def frames(self) -> Iterable[SurveillanceFrame]:
        cache_file = self.cache_path()
        if not cache_file.exists():
            # Optional fetch path: only when creds exist and pyopensky is installed.
            if self.opensky_username and self.opensky_password:
                try:
                    fetched = list(self._fetch_frames_pyopensky())
                    if fetched:
                        self.cache_window(fetched)
                except Exception:
                    # Fetch-to-cache is best-effort; cache-only determinism remains the baseline.
                    pass
            if not cache_file.exists():
                raise FileNotFoundError(
                    f"Replay cache not found for airport={self.airport}; "
                    "set up cache with a recorded window first (or provide OpenSky creds + pyopensky)"
                )
        # Cache format intentionally simple JSON-like dictionary per line.
        for line in cache_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            yield SurveillanceFrame.model_validate_json(line)

    def _fetch_frames_pyopensky(self) -> Iterable[SurveillanceFrame]:
        """Best-effort OpenSky fetch using pyopensky (optional dependency)."""
        try:
            # pyopensky has multiple backends; the Trino client is commonly used for historical windows.
            from pyopensky.trino import Trino  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "pyopensky is not installed; install it to enable OpenSky fetch-to-cache"
            ) from exc
        import os

        # Map vCAS creds into pyopensky's expected environment variables.
        os.environ.setdefault("OPENSKY_USERNAME", self.opensky_username)
        os.environ.setdefault("OPENSKY_PASSWORD", self.opensky_password)

        # We avoid hard-coding an airport database here. Bounding box is a best-effort pad around
        # the configured aerodrome position if present in env, otherwise a generic pad around 0,0.
        # A user can re-run caching with a better bbox via script.
        try:
            from ...config.settings import Settings

            cfg = Settings.from_env()
            center_lat = float(cfg.aerodrome_lat)
            center_lon = float(cfg.aerodrome_lon)
        except Exception:
            center_lat = 0.0
            center_lon = 0.0

        pad = max(0.05, float(self.bbox_pad_deg))
        lon_min = center_lon - pad
        lat_min = center_lat - pad
        lon_max = center_lon + pad
        lat_max = center_lat + pad

        client = Trino()
        stop = self.end
        # The returned object is typically a pandas DataFrame; treat it as an iterable of dict-like rows.
        df = client.history(
            start=self.start,
            stop=stop,
            bounds=(lon_min, lat_min, lon_max, lat_max),
            cached=True,
        )

        # Normalize common OpenSky column names; keep best-effort with defaults.
        # Expected schema in vCAS: lat/lon/alt_m, gs_mps, track_deg, vs_mps.
        for row in getattr(df, "to_dict", lambda orient=None: [])(orient="records"):
            ts = row.get("time") or row.get("timestamp") or row.get("t")
            if ts is None:
                continue
            # pandas Timestamp -> datetime
            try:
                timestamp = ts.to_pydatetime()
            except Exception:
                timestamp = ts if isinstance(ts, datetime) else self.start

            callsign = (row.get("callsign") or "").strip() or (row.get("cs") or "").strip() or "OPENSKY"
            icao24 = (row.get("icao24") or "").strip() or callsign

            lat = row.get("lat") if row.get("lat") is not None else row.get("latitude")
            lon = row.get("lon") if row.get("lon") is not None else row.get("longitude")
            if lat is None or lon is None:
                continue

            alt_m = row.get("baroaltitude")
            if alt_m is None:
                alt_m = row.get("altitude")
            if alt_m is None:
                alt_m = row.get("geoaltitude")
            alt_m = float(alt_m or 0.0)

            gs_mps = row.get("velocity")
            if gs_mps is None:
                gs_mps = row.get("gs")
            gs_mps = float(gs_mps or 0.0)

            track_deg = row.get("heading")
            if track_deg is None:
                track_deg = row.get("track")
            track_deg = float(track_deg or 0.0)

            vs_mps = row.get("vertrate")
            if vs_mps is None:
                vs_mps = row.get("vertical_rate")
            vs_mps = float(vs_mps or 0.0)

            yield SurveillanceFrame(
                timestamp_utc=timestamp,
                source="opensky",
                callsign=callsign,
                icao24=icao24,
                lat=float(lat),
                lon=float(lon),
                alt_m=alt_m,
                gs_mps=gs_mps,
                track_deg=track_deg,
                vs_mps=vs_mps,
            )

    def cache_window(self, frames: Iterable[SurveillanceFrame]) -> None:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_path()
        lines = [frame.model_dump_json() for frame in frames]
        cache_file.write_text("\n".join(lines), encoding="utf-8")

    @property
    def end(self) -> datetime:
        return self.start + timedelta(seconds=self.duration_s)
