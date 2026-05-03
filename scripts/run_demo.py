# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Run a vCAS scenario locally."""

from __future__ import annotations

import argparse
import asyncio

from vcas.config.settings import Settings
from vcas.core import VcasEngine
from vcas.surveillance.adapter import build_frames_with_plans
from vcas.observability import configure_structlog, get_logger

configure_structlog()
LOGGER = get_logger("vcas.scripts.run_demo")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic vCAS scenario")
    parser.add_argument("--scenario", required=True, help="Path to YAML scenario file")
    parser.add_argument("--source", default="synthetic", choices=["synthetic", "replay", "simulator"])
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.source != "synthetic":
        settings = Settings(
            **{
                **settings.__dict__,
                "source_mode": args.source,
                "scenario_path": args.scenario,
            }
        )
    engine = VcasEngine(settings, source_mode=args.source)
    prepared = build_frames_with_plans(settings)
    alerts = asyncio.run(engine.run(prepared.frames, flight_plans=prepared.flight_plans))
    LOGGER.info("run_demo.completed", alerts=len(alerts), source_mode=args.source)
    print(f"alerts={len(alerts)}")
    if not settings.ml_enabled:
        print("vCAS risk mode: deterministic-only (ML disabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
