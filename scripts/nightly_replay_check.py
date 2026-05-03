# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Nightly replay check with optional golden-file diff."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import asyncio

from vcas.config.settings import Settings
from vcas.core import VcasEngine
from vcas.surveillance.adapter import build_frames_with_plans


def _normalize(alert) -> dict[str, Any]:
    return {
        "pair": list(alert.pair),
        "thread_state": alert.thread_state,
        "risk_total": round(alert.risk_total, 6),
        "risk_bucket": alert.bucket,
        "created_utc": alert.created_utc.isoformat(),
    }


def main() -> int:
    settings = Settings.from_env()
    if settings.source_mode != "replay":
        settings = Settings(**{**settings.__dict__, "source_mode": "replay"})

    prepared = build_frames_with_plans(settings)
    frames = list(prepared.frames)
    if not frames:
        print("No replay frames available; skipping nightly replay check.")
        return 0

    engine = VcasEngine(settings=settings, source_mode="replay")
    alerts = asyncio.run(
        engine.run(
        frames=frames,
        flight_plans=prepared.flight_plans,
        )
    )
    observed = [_normalize(alert) for alert in alerts]

    golden_path = Path(os.getenv("VCAS_NIGHTLY_GOLDEN_PATH", "golden/lfbo_1h_alerts.json"))
    if not golden_path.exists():
        print(f"Golden file not found: {golden_path} (creating snapshot for next run).")
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(json.dumps(observed, indent=2), encoding="utf-8")
        return 0

    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    if observed != golden:
        raise SystemExit(
            "Nightly replay alerts do not match committed golden snapshot. "
            f"Observed={len(observed)} expected={len(golden)}"
        )
    print(f"Nightly replay matched golden snapshot: {len(observed)} alerts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
