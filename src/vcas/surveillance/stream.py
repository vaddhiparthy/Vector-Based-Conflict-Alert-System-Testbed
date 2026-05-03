# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Redis and in-memory streaming adapter for surveillance frames."""

from __future__ import annotations

from typing import Iterable, Protocol

from redis import Redis

from .schema import SurveillanceFrame

SURVEILLANCE_STREAM = "surveillance_ingest"


class FrameSink(Protocol):
    async def publish(self, frame: SurveillanceFrame) -> None: ...


class RedisSurveillanceSink:
    """Publish frames to Redis stream when Redis is reachable."""

    def __init__(self, redis_url: str, stream_name: str = SURVEILLANCE_STREAM) -> None:
        self._stream_name = stream_name
        self._redis = Redis.from_url(redis_url, decode_responses=True)

    async def publish(self, frame: SurveillanceFrame) -> None:
        self._redis.xadd(self._stream_name, {"frame": frame.model_dump_json()})


class InMemorySurveillanceSink:
    """Fallback sink used for deterministic tests and no-Redis mode."""

    def __init__(self) -> None:
        self.frames: list[SurveillanceFrame] = []

    async def publish(self, frame: SurveillanceFrame) -> None:
        self.frames.append(frame)


def make_sink(redis_url: str) -> FrameSink:
    """Create a best-effort sink."""
    try:
        sink = RedisSurveillanceSink(redis_url=redis_url)
        sink._redis.ping()
        return sink
    except Exception:
        return InMemorySurveillanceSink()


def parse_stream_frames(items: Iterable[tuple]) -> list[SurveillanceFrame]:
    """Decode Redis stream entries returned by XREAD / XREADGROUP."""
    frames: list[SurveillanceFrame] = []
    for _, payload in items:
        raw = payload.get("frame")
        if isinstance(raw, str):
            frames.append(SurveillanceFrame.model_validate_json(raw))
    return frames
