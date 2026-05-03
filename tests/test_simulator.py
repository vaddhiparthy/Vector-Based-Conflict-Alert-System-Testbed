# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

from vcas.surveillance.simulator.bluesky_runner import BlueSkyRunner, BlueSkyScenario


def test_bluesky_runner_emits_frames_from_waypoint_scenario() -> None:
    runner = BlueSkyRunner(BlueSkyScenario(name="terminal", yaml_path="scenarios/bluesky/terminal_approach_6_waypoints.yml"))
    frames = list(runner.frames())
    assert len(frames) > 0
    assert frames[0].source == "simulator"
    assert frames[0].callsign
