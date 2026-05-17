# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Prometheus metric primitives used by vCAS components."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


FRAME_COUNT = Counter(
    "vcas_frames_processed_total",
    "Total number of surveillance frames processed by the engine.",
)
FRAME_PROCESSING_SECONDS = Histogram(
    "vcas_frame_processing_seconds",
    "Time spent handling a single surveillance frame.",
)

ALERT_COUNT = Counter(
    "vcas_alerts_total",
    "Total number of emitted alert records.",
)

THREAD1_CANDIDATE_PAIRS = Counter(
    "vcas_thread1_candidate_pairs_total",
    "Total screened candidate pairs found by Thread 1.",
)
THREAD1_PROCESS_SECONDS = Histogram(
    "vcas_thread1_processing_seconds",
    "Time spent generating candidate pairs in Thread 1.",
)
THREAD1_LAST_CANDIDATES = Gauge(
    "vcas_thread1_last_candidate_pairs",
    "Candidate pairs generated in the last processed frame.",
)

THREAD2A_INPUTS = Counter(
    "vcas_thread2a_inputs_total",
    "Thread 2A candidates evaluated.",
)
THREAD2A_COUNT = Counter(
    "vcas_thread2a_alerts_total",
    "Total alerts emitted by Thread 2A.",
)
THREAD2A_PROCESS_SECONDS = Histogram(
    "vcas_thread2a_processing_seconds",
    "Time spent in Thread 2A candidate scoring and thresholding.",
)

THREAD2B_INPUTS = Counter(
    "vcas_thread2b_inputs_total",
    "Thread 2B candidates evaluated.",
)
THREAD2B_COUNT = Counter(
    "vcas_thread2b_alerts_total",
    "Total alerts emitted by Thread 2B.",
)
THREAD2B_PROCESS_SECONDS = Histogram(
    "vcas_thread2b_processing_seconds",
    "Time spent in Thread 2B candidate scoring and thresholding.",
)

ACTIVE_AIRCRAFT = Gauge(
    "vcas_active_aircraft",
    "Number of aircraft currently in the engine state table.",
)

WEBSOCKET_SNAPSHOTS_TOTAL = Counter(
    "vcas_websocket_snapshots_total",
    "Total websocket snapshot payloads sent.",
)

WEBSOCKET_CONNECTIONS = Gauge(
    "vcas_websocket_connections",
    "Active websocket connections.",
)

ML_REQUESTS_TOTAL = Counter(
    "vcas_ml_requests_total",
    "Total ML risk lookups attempted.",
)
ML_UNAVAILABLE_REQUESTS = Counter(
    "vcas_ml_unavailable_total",
    "ML risk lookups skipped because the service is unavailable.",
)
