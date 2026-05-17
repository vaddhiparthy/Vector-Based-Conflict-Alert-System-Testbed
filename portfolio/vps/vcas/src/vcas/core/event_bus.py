# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Lightweight async queue abstraction for thread handoff."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, TypeVar

T = TypeVar("T")


class AsyncEventBus:
    """In-memory queue-based transport with small bounded buffers."""

    def __init__(self, maxsize: int = 1024) -> None:
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)

    async def publish(self, value: T) -> None:
        await self._queue.put(value)

    async def subscribe(self) -> AsyncIterator[T]:
        while True:
            yield await self._queue.get()
