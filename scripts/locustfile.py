# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Locust user scenario for vCAS synthetic load testing."""

from __future__ import annotations

import os

from locust import HttpUser, between, events, task


SCENARIO = os.getenv("VCAS_LOCUST_SCENARIO", "scenarios/performance/200_aircraft_30m.yml")
MAX_MS = float(os.getenv("VCAS_LOCUST_MAX_P99_MS", "1200"))


class VCASLoadUser(HttpUser):
    wait_time = between(0.1, 1.0)

    @task
    def run_synthetic(self) -> None:
        response = self.client.get(
            "/api/run-synthetic",
            params={
                "scenario": SCENARIO,
                "with_history": "false",
            },
            name="run_synthetic",
            catch_response=True,
        )
        if response.status_code != 200:
            response.failure(f"non-200 response: {response.status_code}")


@events.quitting.add_listener
def _validate_slo(environment, **_kwargs: object) -> None:  # pragma: no cover
    """Fail the test run if P99 latency drifts too far on the shared endpoint."""
    if not environment.runner:
        return

    stats = environment.stats.get("/api/run-synthetic", "GET")
    if stats is None:
        return

    p99 = stats.get_response_time_percentile(0.99)
    if p99 is not None and p99 > MAX_MS:
        raise SystemExit(f"locust load SLO failed: p99={p99:.1f}ms > {MAX_MS}ms")
