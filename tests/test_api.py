# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

from datetime import datetime, timezone

from vcas.config.settings import Settings
from vcas.core import EngineSnapshot, VcasEngine
from vcas.core.state import AlertRecord
from fastapi.testclient import TestClient
from vcas.api.main import app


def test_run_synthetic_returns_history():
    client = TestClient(app)
    response = client.get(
        "/api/run-synthetic",
        params={"scenario": "scenarios/canonical/head_on.yml", "with_history": "true", "max_history": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_mode"] == "synthetic"
    assert isinstance(payload["history"], list)
    assert len(payload["history"]) <= 10
    assert payload["history"]
    assert payload["history"][0]["frame_index"] > 0
    assert "alerts" in payload


def test_audit_drilldown_from_alert():
    client = TestClient(app)
    settings = Settings.from_env()
    engine = VcasEngine(settings=settings)
    alert = AlertRecord(
        alert_id="manual-alert-1",
        pair=("AC1", "AC2"),
        created_utc=datetime(2026, 4, 27, tzinfo=timezone.utc),
        thread_state="thread2a",
        risk_total=0.77,
        risk_phys=0.77,
        risk_fp=0.0,
        risk_ml=0.0,
        tc_s=45.0,
        d_min_m=250.0,
        bucket="medium",
        metadata={"reason": "unit-test"},
    )
    engine.audit_repo.append(alert)
    engine._alert_row_index[alert.alert_id] = 0
    engine._row_to_frame_index[0] = 4
    engine._last_snapshots = [
        EngineSnapshot(
            frame_index=4,
            timestamp_utc="2026-04-27T00:00:04Z",
            candidate_pairs=1,
            new_alerts=[{"row_id": 0, "alert_id": alert.alert_id}],
            aircraft_count=2,
            total_alerts=1,
            aircraft=[],
        )
    ]
    app.state.engine = engine

    drilldown = client.get("/api/audit-drilldown", params={"alert_id": alert.alert_id})
    assert drilldown.status_code == 200
    details = drilldown.json()
    assert details["alert_id"] == alert.alert_id
    assert details["target_row"]["payload"]["alert_id"] == alert.alert_id
    assert details["row_index"] == 0
    assert details["row_id"] == details["target_row"]["id"]
    assert details["chain"][-1]["id"] == details["row_id"]
    assert any(frame["new_alerts"] for frame in details["trigger_frames"])


def test_metrics_endpoint_exposes_counters():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "vcas_frames_processed_total" in text


def test_client_config_exposes_simple_token_names():
    client = TestClient(app)
    response = client.get("/api/client-config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tokens"]["cesium_env_name"] == "VCAS_CESIUM_TOKEN"
    assert payload["tokens"]["opensky_username_env_name"] == "VCAS_OPENSKY_USERNAME"
    assert payload["tokens"]["opensky_password_env_name"] == "VCAS_OPENSKY_PASSWORD"
    assert "display" in payload
    assert payload["display"]["default_range_nm"] > 0
