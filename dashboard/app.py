# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Streamlit controller for scenario execution, replay scrubbing, and alert drill-down."""


from __future__ import annotations

import asyncio

import streamlit as st

from vcas.config.settings import Settings, TaskMode
from vcas.core import EngineSnapshot, VcasEngine
from vcas.surveillance.adapter import build_frames_with_plans
from vcas.observability import configure_structlog, get_logger

configure_structlog()
LOGGER = get_logger("vcas.dashboard")


def _run(
    mode: TaskMode,
    scenario: str,
    with_history: bool = True,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    settings = Settings.from_env()
    overrides = {"source_mode": mode}
    if scenario:
        overrides["scenario_path"] = scenario
    settings = Settings(**{**settings.__dict__, **overrides})

    engine = VcasEngine(settings=settings, source_mode=mode)
    prepared = build_frames_with_plans(settings)
    alerts, history = asyncio.run(
        engine.run_with_history(
            frames=prepared.frames,
            flight_plans=prepared.flight_plans,
            max_snapshots=(10000 if with_history else 0),
        )
    )
    alert_payload = [
        _to_dict(
            alert,
            row_id=engine.alert_row_id(alert.alert_id),
            frame_index=engine.alert_frame_index(alert.alert_id),
        )
        for alert in alerts
    ]
    history_payload = [_snapshot_to_dict(snapshot) for snapshot in history]
    return (
        alert_payload,
        history_payload,
        [_snapshot_to_dict(snapshot) for snapshot in engine.history()],
        list(engine.audit_repo.all()),
    )


def _to_dict(
    alert: object,
    *,
    row_id: int | None = None,
    frame_index: int | None = None,
) -> dict:
    return {
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
        "row_id": row_id,
        "trigger_frame_index": frame_index,
    }


def _snapshot_to_dict(snapshot: EngineSnapshot) -> dict:
    return {
        "frame_index": snapshot.frame_index,
        "timestamp_utc": snapshot.timestamp_utc,
        "candidate_pairs": snapshot.candidate_pairs,
        "new_alerts": snapshot.new_alerts,
        "aircraft_count": snapshot.aircraft_count,
        "total_alerts": snapshot.total_alerts,
        "aircraft": snapshot.aircraft,
    }


st.title("vCAS Controller")
st.caption("Controller surface with replay scrubber and pair drill-down.")
st.caption(
    "Research-only simulation inspired by Sri Surya Sameer Vaddhiparthy’s blog concept. "
    "See: https://blog.vaddhiparthy.com/2025/11/hybrid-physics-and-aiconcept-for-real.html"
)


if "alerts" not in st.session_state:
    st.session_state["alerts"] = []
if "history" not in st.session_state:
    st.session_state["history"] = []
if "full_history" not in st.session_state:
    st.session_state["full_history"] = []
if "audit_chain" not in st.session_state:
    st.session_state["audit_chain"] = []

col1, col2, col3 = st.columns(3)
with col1:
    source_mode = st.selectbox("Source mode", ["synthetic", "replay", "simulator"], index=0)
with col2:
    scenario = st.text_input("Scenario / source path", value="scenarios/canonical/head_on.yml")
with col3:
    with_history = st.toggle("Capture frame history", value=True, help="Enable for scrubber replay.")

if source_mode != "synthetic":
    st.caption("Replay and simulator modes rely on local adapters. If unavailable, run will fail with a clear error.")

if st.button("Run"):
    try:
        alerts, history, full_history, audit_chain = _run(
            source_mode,
            scenario,
            with_history=with_history,
        )
        LOGGER.info("dashboard.run", source_mode=source_mode, alerts=len(alerts), snapshots=len(history))
        st.session_state["alerts"] = alerts
        st.session_state["history"] = history
        st.session_state["full_history"] = full_history
        st.session_state["audit_chain"] = audit_chain
        st.success(f"Scenario complete. alerts={len(alerts)} snapshots={len(history)}")
    except Exception as error:
        st.error(f"Run failed: {error}")

alerts = st.session_state["alerts"]
history = st.session_state["history"]
full_history = st.session_state["full_history"]
audit_chain = st.session_state["audit_chain"]
chain_lookup = {item["alert_id"]: item for item in alerts}

if not alerts and not history:
    st.stop()

st.subheader("Alert summary")
st.metric("Total alerts", len(alerts))
st.dataframe(alerts)

if history:
    max_index = len(history) - 1
    scrubber = st.slider("Replay scrubber (frame index)", min_value=0, max_value=max_index, value=max_index)
    snapshot = history[scrubber]
    st.subheader("Replay frame")
    st.write(f"Frame {snapshot['frame_index']} • {snapshot['timestamp_utc']} • "
             f"candidate pairs: {snapshot['candidate_pairs']} • aircraft: {snapshot['aircraft_count']}")
    st.json(snapshot["aircraft"])
    st.subheader("New alerts in frame")
    st.json(snapshot["new_alerts"])

pair_choices = sorted({" - ".join(item["pair"]) for item in alerts})
if pair_choices:
    st.subheader("Pair drill-down")
    pair = st.selectbox("Pair", pair_choices)
    left, right = pair.split(" - ")
    pair_frames = [
        row
        for row in alerts
        if set(row["pair"]) == {left, right}
    ]
    st.write(f"Matching alerts in chain: {len(pair_frames)}")
    st.dataframe(pair_frames)

alert_choices = sorted(alerts, key=lambda item: item["created_utc"])
if alert_choices:
    st.subheader("Audit drill-down")
    selected_alert_id = st.selectbox(
        "Alert",
        options=[item["alert_id"] for item in alert_choices],
    )
    selected_alert = chain_lookup[selected_alert_id]
    row_index = selected_alert.get("row_id")
    frame_index = selected_alert.get("trigger_frame_index")
    selected_row_id = row_index + 1 if isinstance(row_index, int) else None
    st.write("Selected alert")
    st.json(selected_alert)

    if row_index is not None and row_index >= 0:
        target_chain = audit_chain[: selected_row_id if selected_row_id is not None else None]
        st.write(f"Audit row chain (rows 1..{selected_row_id})")
        chain_preview = [
            {
                "row_id": row["id"],
                "created_utc": row["created_utc"],
                "alert_id": row["payload"].get("alert_id"),
                "pair": row["payload"].get("pair"),
                "bucket": row["payload"].get("bucket"),
                "thread_state": row["payload"].get("thread_state"),
                "risk_total": row["payload"].get("risk_total"),
            }
            for row in target_chain
        ]
        st.dataframe(chain_preview)

        if frame_index is not None:
            st.write(f"Trigger frame (frame index: {frame_index})")
            trigger_snapshots = [snap for snap in full_history if snap["frame_index"] == frame_index]
        else:
            trigger_snapshots = [
                snap
                for snap in full_history
                if any(alert_row.get("row_id") == row_index for alert_row in snap.get("new_alerts", []))
            ]
            st.write(f"Exact trigger frames for row {selected_row_id}")
        if trigger_snapshots:
            if len(trigger_snapshots) == 1:
                st.json(trigger_snapshots[0])
            else:
                st.dataframe(
                    [
                        {key: value for key, value in snap.items() if key != "aircraft"}
                        for snap in trigger_snapshots
                    ]
                )
        else:
            st.warning("No trigger frame found for this alert.")
