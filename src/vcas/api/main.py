# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""FastAPI app for vCAS streaming, audit, and simulation control."""

from __future__ import annotations

import asyncio
import base64
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..config.settings import Settings, TaskMode
from ..core import EngineSnapshot, VcasEngine
from ..core.state import AlertRecord
from ..surveillance.adapter import build_frames_with_plans
from ..observability import (
    WEBSOCKET_CONNECTIONS,
    WEBSOCKET_SNAPSHOTS_TOTAL,
    configure_structlog,
    configure_otlp_exporter,
    configure_tracing,
)
from ..observability import get_logger
from ..surveillance.simulator.random_traffic import Aerodrome, generate_random_waypoint_scenario

configure_tracing()
configure_otlp_exporter()
configure_structlog()
LOGGER = get_logger("vcas.api")


app = FastAPI(title="vCAS", version="0.1.0")
_demo_root = None
for candidate in Path(__file__).resolve().parents:
    maybe_web = candidate / "web"
    if maybe_web.exists() and (maybe_web / "index.html").exists():
        _demo_root = maybe_web
        break
if _demo_root is not None and _demo_root.exists():
    app.mount("/demo", StaticFiles(directory=str(_demo_root), html=True), name="demo")


class ScreenshotSaveRequest(BaseModel):
    name: str = Field(default="vcas")
    png_base64: str = Field(..., description="Data URL or raw base64 for PNG bytes")


class GenerateScenarioRequest(BaseModel):
    seed: int | None = Field(default=None, description="RNG seed (omit for auto)")
    bg_count: int = Field(default=18, ge=0, le=80)
    duration_s: int = Field(default=600, ge=120, le=1800)
    dt_s: float = Field(default=1.0, ge=0.2, le=5.0)


def _safe_filename(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "_", value)
    value = value.strip("._-") or "vcas"
    return value[:64]


@app.post("/api/save-screenshot")
async def save_screenshot(req: ScreenshotSaveRequest) -> dict[str, str]:
    raw = req.png_base64.strip()
    if raw.startswith("data:"):
        comma = raw.find(",")
        if comma == -1:
            raise HTTPException(status_code=400, detail="Invalid data URL")
        raw = raw[comma + 1 :]

    try:
        payload = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 payload") from exc

    # Keep outputs inside the repo tree, near other agent artifacts.
    out_dir = (Path(__file__).resolve().parents[3] / "agent_downloads" / "screenshots").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = _safe_filename(req.name)
    out_path = (out_dir / f"{ts}_{name}.png").resolve()
    if out_dir not in out_path.parents:
        raise HTTPException(status_code=400, detail="Invalid output path")

    out_path.write_bytes(payload)
    return {"saved_to": str(out_path)}


@app.post("/api/generate-scenario")
async def generate_scenario(req: GenerateScenarioRequest) -> dict[str, object]:
    """Generate a seeded random waypoint scenario and save it inside the repo.

    Returns the relative scenario path you can paste into the UIs.
    """

    settings = Settings.from_env()
    seed = int(req.seed) if req.seed is not None else int(datetime.now(tz=timezone.utc).timestamp())
    scenario = generate_random_waypoint_scenario(
        seed=seed,
        aerodrome=Aerodrome(lat=settings.aerodrome_lat, lon=settings.aerodrome_lon, alt_m=settings.aerodrome_alt_m),
        bg_count=req.bg_count,
        duration_s=req.duration_s,
        dt_s=req.dt_s,
    )

    repo_root = Path(__file__).resolve().parents[3]
    out_dir = (repo_root / "scenarios" / "generated").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel_path = Path("scenarios") / "generated" / f"{ts}_random_{seed}.yml"
    out_path = (repo_root / rel_path).resolve()
    if out_dir not in out_path.parents:
        raise HTTPException(status_code=400, detail="Invalid output path")

    out_path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    return {"seed": seed, "scenario_path": str(rel_path).replace("\\", "/")}


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "utc": datetime.now(tz=timezone.utc).isoformat(),
        "ml_enabled": Settings.from_env().ml_enabled,
    }


@app.get("/api/audit-chain-verify")
async def verify_chain() -> dict[str, int | None]:
    engine = app.state.engine
    broken = engine.audit_repo.verify_chain() if engine else None
    return {"broken_row_id": broken}


@app.get("/api/alerts")
async def alerts() -> list[dict]:
    engine = app.state.engine
    if not engine:
        return []
    return [row["payload"] for row in engine.audit_repo.all()]


def _alert_to_dict(
    alert: AlertRecord,
    *,
    row_id: int | None = None,
    frame_index: int | None = None,
) -> dict[str, object]:
    payload = {
        "pair": list(alert.pair),
        "alert_id": alert.alert_id,
        "created_utc": alert.created_utc.isoformat(),
        "thread_state": alert.thread_state,
        "risk_total": alert.risk_total,
        "risk_phys": alert.risk_phys,
        "risk_fp": alert.risk_fp,
        "risk_ml": alert.risk_ml,
        "tc_s": alert.tc_s,
        "d_min_m": alert.d_min_m,
        "bucket": alert.bucket,
        "metadata": alert.metadata,
    }
    if row_id is not None:
        payload["row_id"] = row_id
    if frame_index is not None:
        payload["trigger_frame_index"] = frame_index
    return payload


def _snapshot_to_dict(snapshot: EngineSnapshot) -> dict[str, object]:
    return {
        "frame_index": snapshot.frame_index,
        "timestamp_utc": snapshot.timestamp_utc,
        "candidate_pairs": snapshot.candidate_pairs,
        "new_alerts": snapshot.new_alerts,
        "aircraft_count": snapshot.aircraft_count,
        "total_alerts": snapshot.total_alerts,
        "aircraft": snapshot.aircraft,
    }


@app.get("/api/client-config")
async def client_config() -> dict[str, object]:
    settings = Settings.from_env()
    return {
        "cesium_token": settings.cesium_token,
        "aerodrome": {
            "lat": settings.aerodrome_lat,
            "lon": settings.aerodrome_lon,
            "alt_m": settings.aerodrome_alt_m,
        },
        "display": {
            "default_range_nm": 20,
            "default_refresh_ms": 120,
        },
        "tokens": {
            "cesium_env_name": "VCAS_CESIUM_TOKEN",
            "opensky_username_env_name": "VCAS_OPENSKY_USERNAME",
            "opensky_password_env_name": "VCAS_OPENSKY_PASSWORD",
            "telegram_env_name": "TELEGRAM_BOT_TOKEN",
            "openweather_env_name": "OPENWEATHER_API_KEY",
        },
    }


def _coerce_source_mode(value: str) -> TaskMode:
    mode = (value or "synthetic").strip().lower()
    if mode in {"synthetic", "replay", "simulator"}:
        return mode
    raise HTTPException(status_code=400, detail=f"unsupported source_mode={mode}")


def _visible_snapshots(
    snapshots: list[EngineSnapshot],
    *,
    max_history: int | None,
) -> list[EngineSnapshot]:
    if max_history is None:
        return snapshots
    return snapshots[-max_history:]


def _row_for_frame(snapshots: list[EngineSnapshot], row_index: int) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for snapshot in snapshots:
        for alert_payload in snapshot.new_alerts:
            if alert_payload.get("row_id") == row_index:
                frames.append(_snapshot_to_dict(snapshot))
                break
    return frames


@app.get("/api/audit-drilldown")
async def audit_drilldown(alert_id: str) -> dict[str, object]:
    engine = app.state.engine
    if engine is None:
        raise HTTPException(status_code=404, detail="No active engine. Run a scenario first.")

    row_index = engine.alert_row_id(alert_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail=f"alert_id not found: {alert_id}")

    chain = list(engine.audit_repo.all())
    if row_index >= len(chain):
        raise HTTPException(status_code=404, detail=f"alert_id not found: {alert_id}")

    target_chain_row = chain[row_index]
    trigger_frames = _row_for_frame(engine.history(), row_index=row_index)
    return {
        "alert_id": alert_id,
        "row_index": row_index,
        "row_id": target_chain_row["id"],
        "target_row": target_chain_row,
        "chain": chain[: row_index + 1],
        "trigger_frames": trigger_frames,
    }


@app.get("/api/run")
async def run_capture(
    scenario: str | None = Query(default=None, description="Scenario YAML path for synthetic mode"),
    source_mode: str = Query(default="synthetic", description="synthetic | replay | simulator"),
    with_history: bool = Query(default=False),
    max_history: int | None = Query(default=None, ge=1),
    include_audit_chain: bool = Query(default=False),
) -> dict[str, object]:
    LOGGER.info("api.run_capture", source_mode=source_mode, with_history=with_history, max_history=max_history)
    settings = Settings.from_env()
    mode = _coerce_source_mode(source_mode)
    overrides = {"source_mode": mode}
    if scenario:
        overrides["scenario_path"] = scenario
    settings = Settings(**{**settings.__dict__, **overrides})
    engine = VcasEngine(settings=settings, source_mode=mode)
    app.state.engine = engine
    prepared = build_frames_with_plans(settings)
    frames = prepared.frames

    if with_history:
        alerts, _ = await engine.run_with_history(
            frames=frames,
            flight_plans=prepared.flight_plans,
            max_snapshots=max_history,
        )
    else:
        alerts = await engine.run(
            frames=frames,
            flight_plans=prepared.flight_plans,
        )

    banner = "deterministic-only" if not settings.ml_enabled else "ml_enabled"
    all_snapshots = engine.history()
    history = [_snapshot_to_dict(snapshot) for snapshot in _visible_snapshots(all_snapshots, max_history=max_history)] if with_history else []
    return {
        "alerts": [
            _alert_to_dict(
                alert,
                row_id=engine.alert_row_id(alert.alert_id),
                frame_index=engine.alert_frame_index(alert.alert_id),
            )
            for alert in alerts
        ],
        "aircraft_count": len(engine.aircraft_repo.all()),
        "alert_count": len(alerts),
        "broken_row_id": engine.audit_repo.verify_chain(),
        "risk_mode": banner,
        "source_mode": settings.source_mode,
        "history": history,
        "audit_chain": list(engine.audit_repo.all()) if include_audit_chain else [],
    }


@app.get("/api/run-synthetic")
async def run_synthetic(
    scenario: str = Query(..., description="Scenario YAML path"),
    with_history: bool = Query(default=False),
    max_history: int | None = Query(default=None, ge=1),
    include_audit_chain: bool = Query(default=False),
) -> dict[str, object]:
    return await run_capture(
        scenario=scenario,
        source_mode="synthetic",
        with_history=with_history,
        max_history=max_history,
        include_audit_chain=include_audit_chain,
    )


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/surveillance")
async def ws_surveillance(ws: WebSocket) -> None:
    await ws.accept()
    WEBSOCKET_CONNECTIONS.inc()
    try:
        while True:
            engine = getattr(app.state, "engine", None)
            if engine is None:
                await ws.send_json({"type": "empty", "aircraft": [], "alerts": []})
            else:
                aircraft = []
                for item in sorted(engine.aircraft_repo.all(), key=lambda item: item.callsign):
                    lat, lon, alt_m = engine.converter.enu_to_geodetic(
                        float(item.state.position_m[0]),
                        float(item.state.position_m[1]),
                        float(item.state.position_m[2]),
                    )
                    aircraft.append(
                        {
                            "callsign": item.callsign,
                            "icao24": item.state.icao24,
                            "position": item.state.position_m.tolist(),
                            "lat": lat,
                            "lon": lon,
                            "alt_m": alt_m,
                            "velocity": item.state.velocity_mps.tolist(),
                            "timestamp_utc": item.ingested_utc.isoformat(),
                        }
                    )
                events = [row["payload"] for row in engine.audit_repo.all()]
                await ws.send_json(jsonable_encoder({"type": "snapshot", "aircraft": aircraft, "alerts": events}))
            WEBSOCKET_SNAPSHOTS_TOTAL.inc()
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
    finally:
        WEBSOCKET_CONNECTIONS.dec()
