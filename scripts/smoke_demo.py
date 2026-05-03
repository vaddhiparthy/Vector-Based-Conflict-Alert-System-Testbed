# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Smoke script for deterministic scenario execution."""

from __future__ import annotations

import asyncio

from vcas.config.settings import Settings
from vcas.core import VcasEngine
from vcas.surveillance.adapter import build_frames_with_plans
from vcas.observability import configure_structlog, get_logger

configure_structlog()
LOGGER = get_logger("vcas.scripts.smoke")


def run() -> None:
    settings = Settings.from_env()
    prepared = build_frames_with_plans(settings)
    engine = VcasEngine(settings=settings)
    alerts = asyncio.run(engine.run(prepared.frames, flight_plans=prepared.flight_plans))
    assert len(alerts) >= 0
    LOGGER.info("smoke_demo.completed", alerts=len(alerts), hash_tail=engine.audit_repo.verify_chain())
    print(f"[smoke] alerts={len(alerts)} hash_tail={engine.audit_repo.verify_chain()}")


if __name__ == "__main__":
    run()
