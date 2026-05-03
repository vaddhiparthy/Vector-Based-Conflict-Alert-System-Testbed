# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Observability helpers for vCAS instrumentation."""

from .metrics import (
    ACTIVE_AIRCRAFT,
    ALERT_COUNT,
    FRAME_COUNT,
    FRAME_PROCESSING_SECONDS,
    ML_REQUESTS_TOTAL,
    ML_UNAVAILABLE_REQUESTS,
    THREAD1_CANDIDATE_PAIRS,
    THREAD1_LAST_CANDIDATES,
    THREAD1_PROCESS_SECONDS,
    THREAD2A_COUNT,
    THREAD2A_INPUTS,
    THREAD2A_PROCESS_SECONDS,
    THREAD2B_COUNT,
    THREAD2B_INPUTS,
    THREAD2B_PROCESS_SECONDS,
    WEBSOCKET_CONNECTIONS,
    WEBSOCKET_SNAPSHOTS_TOTAL,
)
from .tracing import configure_otlp_exporter, configure_tracing, traced_span
from .logging import configure_structlog, get_logger

__all__ = [
    "ACTIVE_AIRCRAFT",
    "ALERT_COUNT",
    "FRAME_COUNT",
    "FRAME_PROCESSING_SECONDS",
    "ML_REQUESTS_TOTAL",
    "ML_UNAVAILABLE_REQUESTS",
    "THREAD1_CANDIDATE_PAIRS",
    "THREAD1_LAST_CANDIDATES",
    "THREAD1_PROCESS_SECONDS",
    "THREAD2A_COUNT",
    "THREAD2A_INPUTS",
    "THREAD2A_PROCESS_SECONDS",
    "THREAD2B_COUNT",
    "THREAD2B_INPUTS",
    "THREAD2B_PROCESS_SECONDS",
    "WEBSOCKET_CONNECTIONS",
    "WEBSOCKET_SNAPSHOTS_TOTAL",
    "configure_otlp_exporter",
    "configure_tracing",
    "traced_span",
    "configure_structlog",
    "get_logger",
]
