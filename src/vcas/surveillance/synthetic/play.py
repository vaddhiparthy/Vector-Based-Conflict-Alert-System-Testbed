# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""CLI to publish synthetic scenario frames into the ingestion stream."""

from __future__ import annotations

import argparse
import asyncio

from ...config.settings import Settings
from ...surveillance.stream import FrameSink, make_sink
from .generator import load_scenario, load_track_frames


async def _publish(sink: FrameSink, path: str) -> None:
    scenario = load_scenario(path)
    for frame in load_track_frames(scenario):
        await sink.publish(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a synthetic scenario as frames.")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML")
    parser.add_argument(
        "--rate-hz",
        type=float,
        default=1.0,
        help="Rate at which frames are emitted",
    )
    parser.add_argument("--sleep", action="store_true", help="Sleep to emulate real-time pacing")
    args = parser.parse_args()

    settings = Settings.from_env()
    sink = make_sink(settings.redis_url)
    delay = 1.0 / max(args.rate_hz, 0.1)
    for frame in load_track_frames(load_scenario(args.scenario)):
        asyncio.run(sink.publish(frame))
        if args.sleep:
            import time

            time.sleep(delay)
    return None


if __name__ == "__main__":
    main()
