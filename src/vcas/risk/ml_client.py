# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Async ML client with fallback and a lightweight circuit-breaker."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ..core.state import ConflictCandidate
from ..observability import ML_REQUESTS_TOTAL, ML_UNAVAILABLE_REQUESTS

DEFAULT_ML_URL = "http://localhost:8080/predictions/vcas-lstm"
DEFAULT_TIMEOUT_S = 1.2
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_OPEN_FOR_SECONDS = 30.0


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass
class _CircuitState:
    failure_count: int = 0
    opened_until: float | None = None


_circuit_state = _CircuitState()
_circuit_lock = threading.Lock()
_ML_URL = os.getenv("VCAS_ML_SERVICE_URL", DEFAULT_ML_URL)
_REQ_TIMEOUT_S = _env_float("VCAS_ML_TIMEOUT_S", DEFAULT_TIMEOUT_S)
_FAIL_THRESHOLD = _env_int("VCAS_ML_CIRCUIT_FAILURE_THRESHOLD", DEFAULT_FAILURE_THRESHOLD)
_OPEN_FOR_S = _env_float("VCAS_ML_CIRCUIT_OPEN_SECONDS", DEFAULT_OPEN_FOR_SECONDS)


def _is_service_open(now: float) -> bool:
    with _circuit_lock:
        opened = _circuit_state.opened_until
        if opened is None:
            return False
        if now < opened:
            return True
        _circuit_state.opened_until = None
        return False


def _record_failure() -> None:
    with _circuit_lock:
        _circuit_state.failure_count += 1
        if _circuit_state.failure_count >= _FAIL_THRESHOLD and _OPEN_FOR_S > 0:
            _circuit_state.opened_until = time.monotonic() + _OPEN_FOR_S


def _record_success() -> None:
    with _circuit_lock:
        _circuit_state.failure_count = 0
        _circuit_state.opened_until = None


def _extract_predictions(payload: dict) -> list[float]:
    if isinstance(payload, dict):
        candidates: list[object] = []
        if "predictions" in payload:
            candidates = payload["predictions"]  # type: ignore[assignment]
        elif "outputs" in payload:
            candidates = payload["outputs"]  # type: ignore[assignment]
        elif "data" in payload:
            candidates = payload["data"]  # type: ignore[assignment]
        elif "prediction" in payload:
            candidates = [payload["prediction"]]  # type: ignore[list-item]
        else:
            candidates = []
        if candidates is None:
            candidates = []
        if isinstance(candidates, list):
            return [_coerce_probability(item) for item in candidates]
        return [_coerce_probability(candidates)]

    if isinstance(payload, list):
        return [_coerce_probability(item) for item in payload]

    return []


def _coerce_probability(value: object) -> float:
    if isinstance(value, dict):
        if "score" in value and isinstance(value["score"], (int, float)):
            return float(value["score"])
        if "probability" in value and isinstance(value["probability"], (int, float)):
            return float(value["probability"])
        return 0.0
    if isinstance(value, (int, float, np.number)):
        return float(value)
    return 0.0


def _post_predictions(url: str, payload: dict, timeout_s: float) -> str:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        return response.read().decode("utf-8")


def _fallback(values: int) -> np.ndarray:
    return np.zeros((values,), dtype=float)


def build_feature_matrix(candidate: ConflictCandidate, *, sample_count: int = 8) -> np.ndarray:
    """Build a deterministic sequence of ML-style features for a conflict candidate.

    Features are ``[dx, dy, dz, |dv|, bearing_deg, tc_s]``.
    """

    if candidate is None:
        return np.zeros((0, 6), dtype=float)
    history_a = list(candidate.history_a)
    history_b = list(candidate.history_b)
    pair_len = min(len(history_a), len(history_b), sample_count)
    if pair_len == 0:
        rel_pos = candidate.b.position_m - candidate.a.position_m
        rel_vel = candidate.b.velocity_mps - candidate.a.velocity_mps
        rel_speed = float(np.linalg.norm(rel_vel))
        bearing_deg = float((np.degrees(np.arctan2(rel_pos[0], rel_pos[1])) + 360.0) % 360.0)
        tc = candidate.time_to_conflict_s if candidate.time_to_conflict_s is not None else 0.0
        return np.array([[rel_pos[0], rel_pos[1], rel_pos[2], rel_speed, bearing_deg, tc]], dtype=float)

    features: list[list[float]] = []
    for (_, state_a), (_, state_b) in zip(history_a[-pair_len:], history_b[-pair_len:]):
        # Guard against malformed history lengths and keep deterministic shape.
        rel_pos = state_b.position_m - state_a.position_m
        rel_vel = state_b.velocity_mps - state_a.velocity_mps
        rel_speed = float(np.linalg.norm(rel_vel))
        bearing_deg = float((np.degrees(np.arctan2(rel_pos[0], rel_pos[1])) + 360.0) % 360.0)
        tc = candidate.time_to_conflict_s if candidate.time_to_conflict_s is not None else 0.0
        features.append([rel_pos[0], rel_pos[1], rel_pos[2], rel_speed, bearing_deg, tc])

    if not features:
        return _fallback(1).reshape((1, 6))
    return np.asarray(features, dtype=float)


async def p_ml(
    sequences: np.ndarray | Iterable[Iterable[float]],
    *,
    service_healthy: bool = False,
    service_url: str | None = None,
    timeout_s: float | None = None,
) -> np.ndarray:
    """Ask the ML endpoint for `p_ml`; fallback to zeros on any service failure."""

    ML_REQUESTS_TOTAL.inc()
    matrix = np.asarray(list(sequences), dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    count = len(matrix)
    if count == 0:
        return _fallback(0)
    if not service_healthy:
        ML_UNAVAILABLE_REQUESTS.inc()
        return _fallback(count)

    url = service_url or _ML_URL
    timeout = _REQ_TIMEOUT_S if timeout_s is None else timeout_s
    now = time.monotonic()
    if _is_service_open(now):
        ML_UNAVAILABLE_REQUESTS.inc()
        return _fallback(count)

    payload = {"instances": matrix.tolist()}
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(_post_predictions, url, payload, timeout),
            timeout=timeout,
        )
    except (TimeoutError, OSError, urllib.error.URLError, urllib.error.HTTPError):
        _record_failure()
        ML_UNAVAILABLE_REQUESTS.inc()
        return _fallback(count)

    try:
        body = json.loads(raw)
        probs = _extract_predictions(body)
        _record_success()
        if not probs:
            return _fallback(count)
    except Exception:
        _record_failure()
        ML_UNAVAILABLE_REQUESTS.inc()
        return _fallback(count)

    result = np.asarray(probs, dtype=float)
    result = np.clip(result, 0.0, 1.0)
    if result.size == 0:
        return _fallback(count)
    if result.size != count:
        # Keep caller-safe and deterministic by clipping/padding to expected count.
        if result.size > count:
            return result[:count]
        return np.pad(result, (0, max(0, count - result.size)))
    return result
