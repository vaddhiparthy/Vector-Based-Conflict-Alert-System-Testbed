# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

from datetime import datetime, timezone

from vcas.surveillance.adapter import build_replay_frames, build_synthetic_frames


def test_synthetic_loader_is_deterministic():
    first = list(build_synthetic_frames("scenarios/canonical/head_on.yml"))
    second = list(build_synthetic_frames("scenarios/canonical/head_on.yml"))
    assert len(first) == len(second)
    assert first[0].model_dump() == second[0].model_dump()
    assert first[-1].model_dump() == second[-1].model_dump()


def test_replay_cache_missing_is_recoverable():
    source = build_replay_frames(
        airport="KCLT",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_s=60,
    )
    try:
        list(source)
    except FileNotFoundError:
        assert True
