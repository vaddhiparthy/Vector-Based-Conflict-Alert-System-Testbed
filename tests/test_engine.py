# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

import asyncio

from vcas.config.settings import Settings
from vcas.core import VcasEngine
from vcas.surveillance.adapter import build_synthetic_frames


def test_head_on_engine_produces_alerts():
    settings = Settings.from_env()
    engine = VcasEngine(settings=settings)
    alerts = asyncio.run(engine.run(build_synthetic_frames("scenarios/canonical/head_on.yml")))
    assert len(engine.aircraft_repo.all()) > 0
    assert len(alerts) >= 0
    assert engine.audit_repo.verify_chain() is None


def test_run_with_history_records_snapshots():
    settings = Settings.from_env()
    engine = VcasEngine(settings=settings)
    alerts, snapshots = asyncio.run(
        engine.run_with_history(
            build_synthetic_frames("scenarios/canonical/head_on.yml"),
            max_snapshots=5,
        )
    )
    assert len(snapshots) == 5
    assert snapshots[0].frame_index > 0
    assert snapshots[-1].total_alerts == len(alerts)
    assert snapshots[0].aircraft
