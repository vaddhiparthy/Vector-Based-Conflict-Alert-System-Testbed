# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Runtime orchestrator for ingestion and conflict pipelines."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Iterable

import numpy as np

from ..config.settings import Settings
from ..core.state import AlertRecord, AircraftStateEnvelope
from ..flightplan import FlightPlan
from ..geo.coords import EnuConverter, ReferencePoint
from ..observability import ACTIVE_AIRCRAFT, FRAME_COUNT, FRAME_PROCESSING_SECONDS, get_logger, traced_span
from ..physics.state import AircraftState
from ..storage.repositories import AircraftRepo, AuditRepo
from ..surveillance.schema import SurveillanceFrame
from ..threads import Thread1Worker, Thread2AWorker, Thread2BWorker
from ..wind import WindProfile, resolve_wind


@dataclass(frozen=True)
class EngineSnapshot:
    """Lightweight frame-by-frame execution snapshot for replay scrubbers."""

    frame_index: int
    timestamp_utc: str
    candidate_pairs: int
    new_alerts: list[dict]
    aircraft_count: int
    total_alerts: int
    aircraft: list[dict]


class VcasEngine:
    """Single-process deterministic orchestration loop."""

    def __init__(self, settings: Settings, source_mode: str = "synthetic") -> None:
        self._logger = get_logger("vcas.engine")
        self.settings = settings
        self.source_mode = source_mode
        self.aircraft_repo = AircraftRepo()
        self.audit_repo = AuditRepo()

        self.converter = EnuConverter(
            ReferencePoint(
                latitude_deg=settings.aerodrome_lat,
                longitude_deg=settings.aerodrome_lon,
                altitude_m=settings.aerodrome_alt_m,
            )
        )
        self.thread1 = Thread1Worker(
            threshold_s=settings.t_thread1_s,
            protected_radius_m=settings.protected_radius_m,
            protected_height_m=settings.protected_height_m,
        )
        self.thread2a = Thread2AWorker(
            settings=settings,
            output_bus=None,
            audit_repo=self.audit_repo,
            converter=self.converter,
        )
        self.thread2b = Thread2BWorker(
            settings=settings,
            output_bus=None,
            audit_repo=self.audit_repo,
            converter=self.converter,
        )
        self._last_snapshots: list[EngineSnapshot] = []
        self._alert_row_index: dict[str, int] = {}
        self._row_to_frame_index: dict[int, int] = {}
        self._state_history: dict[str, deque[tuple[datetime, AircraftState]]] = {}
        self._flight_plans: dict[str, FlightPlan] = {}
        self._wind_profile = WindProfile.from_path(settings.wind_profile_path)

    def frame_to_state(self, frame: SurveillanceFrame) -> AircraftState:
        pos = self.converter.geodetic_to_enu(frame.lat, frame.lon, frame.alt_m)
        v_north = frame.gs_mps * np.cos(np.deg2rad(frame.track_deg))
        v_east = frame.gs_mps * np.sin(np.deg2rad(frame.track_deg))
        wind = resolve_wind(altitude_m=frame.alt_m, profile=self._wind_profile)
        velocity = np.array([v_east, v_north, frame.vs_mps], dtype=float) + wind
        return AircraftState(
            callsign=frame.callsign,
            icao24=frame.icao24,
            timestamp=frame.timestamp_utc.astimezone(timezone.utc),
            alt_m=float(frame.alt_m),
            position_m=pos,
            velocity_mps=velocity,
        )

    def _aircraft_snapshot(self, item: AircraftStateEnvelope) -> dict[str, object]:
        lat_deg, lon_deg, alt_m = self.converter.enu_to_geodetic(
            float(item.state.position_m[0]),
            float(item.state.position_m[1]),
            float(item.state.position_m[2]),
        )
        return {
            "callsign": item.callsign,
            "icao24": item.state.icao24,
            "timestamp_utc": item.ingested_utc.isoformat(),
            "position_m": item.state.position_m.tolist(),
            "lat": lat_deg,
            "lon": lon_deg,
            "alt_m": alt_m,
            "velocity_mps": item.state.velocity_mps.tolist(),
            "source": item.source,
        }

    def _serialize_alert(self, alert: AlertRecord) -> dict[str, object]:
        return {
            "alert_id": alert.alert_id,
            "pair": list(alert.pair),
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

    def history(self) -> list[EngineSnapshot]:
        return list(self._last_snapshots)

    def alert_row_id(self, alert_id: str) -> int | None:
        return self._alert_row_index.get(alert_id)

    def alert_frame_index(self, alert_id: str) -> int | None:
        row_id = self.alert_row_id(alert_id)
        if row_id is None:
            return None
        return self._row_to_frame_index.get(row_id)

    async def run(self, frames: Iterable[SurveillanceFrame], *, flight_plans: dict[str, FlightPlan] | None = None) -> list[AlertRecord]:
        alerts: list[AlertRecord] = []
        self._alert_row_index.clear()
        self._row_to_frame_index.clear()
        self._state_history.clear()
        self._flight_plans = {key.upper(): value for key, value in (flight_plans or {}).items()}
        max_history = max(1, self.settings.flight_plan_window_s)

        frame_index = -1
        current_time = None
        group_index = 0
        def _prune_stale(ts):
            # Drop aircraft that haven't updated recently (end-of-route / spawn/despawn realism).
            stale_before = ts - timedelta(seconds=2)
            for item in list(self.aircraft_repo.all()):
                if item.ingested_utc < stale_before:
                    self.aircraft_repo.remove(item.callsign)

        def _consume_group(ts):
            nonlocal group_index
            if ts is None:
                return []
            _prune_stale(ts)
            return self.thread1.process_states(
                self.aircraft_repo.all(),
                frame_timestamp_utc=ts,
                flight_plans=self._flight_plans,
                state_histories=self._state_history,
            )

        for frame_index, frame in enumerate(frames):
            FRAME_COUNT.inc()
            frame_time = frame.timestamp_utc.astimezone(timezone.utc)

            # When the timestamp advances, run the conflict scan once for the previous tick.
            if current_time is not None and frame_time != current_time:
                candidates = _consume_group(current_time)
                for candidate in candidates:
                    alert_a = await self.thread2a.consume(candidate)
                    if alert_a is not None:
                        alerts.append(alert_a)
                        row_id = len(self.audit_repo.rows)
                        self._alert_row_index[alert_a.alert_id] = row_id
                        self._row_to_frame_index[row_id] = group_index
                    alert_b = await self.thread2b.consume(candidate)
                    if alert_b is not None:
                        alerts.append(alert_b)
                        row_id = len(self.audit_repo.rows)
                        self._alert_row_index[alert_b.alert_id] = row_id
                        self._row_to_frame_index[row_id] = group_index
                group_index += 1

            current_time = frame_time if current_time is None else current_time
            if frame_time != current_time:
                current_time = frame_time

            with FRAME_PROCESSING_SECONDS.time():
                with traced_span(
                    "engine.frame.ingest",
                    attributes={"frame.index": str(frame_index), "frame.timestamp_utc": frame_time.isoformat()},
                ):
                    state = self.frame_to_state(frame)
                    envelope = AircraftStateEnvelope(
                        callsign=state.normalized_callsign(),
                        state=state,
                        source=frame.source,
                        ingested_utc=frame_time,
                    )
                    self.aircraft_repo.upsert(envelope)
                    history = self._state_history.setdefault(state.normalized_callsign(), deque(maxlen=max_history))
                    history.append((frame_time, state))
                    ACTIVE_AIRCRAFT.set(len(self.aircraft_repo.all()))

        # Final tick scan.
        if current_time is not None:
            candidates = _consume_group(current_time)
            for candidate in candidates:
                alert_a = await self.thread2a.consume(candidate)
                if alert_a is not None:
                    alerts.append(alert_a)
                    row_id = len(self.audit_repo.rows)
                    self._alert_row_index[alert_a.alert_id] = row_id
                    self._row_to_frame_index[row_id] = group_index
                alert_b = await self.thread2b.consume(candidate)
                if alert_b is not None:
                    alerts.append(alert_b)
                    row_id = len(self.audit_repo.rows)
                    self._alert_row_index[alert_b.alert_id] = row_id
                    self._row_to_frame_index[row_id] = group_index
            group_index += 1

        self._logger.info(
            "engine.run.done",
            frames_processed=frame_index + 1 if "frame_index" in locals() else 0,
            alerts_emitted=len(alerts),
        )
        return alerts

    async def run_with_history(
        self,
        frames: Iterable[SurveillanceFrame],
        *,
        flight_plans: dict[str, FlightPlan] | None = None,
        max_snapshots: int | None = None,
    ) -> tuple[list[AlertRecord], list[EngineSnapshot]]:
        alerts: list[AlertRecord] = []
        all_snapshots: list[EngineSnapshot] = []
        visible_snapshots: list[EngineSnapshot] = []
        self._alert_row_index.clear()
        self._row_to_frame_index.clear()
        self._state_history.clear()
        self._flight_plans = {key.upper(): value for key, value in (flight_plans or {}).items()}
        max_history = max(1, self.settings.flight_plan_window_s)
        self._logger.info(
            "engine.run_with_history.start",
            frames=0,
            source_mode=self.source_mode,
            flight_plans=len(self._flight_plans),
        )

        last_snapshot_time = None
        pending_alerts: list[dict] = []
        pending_candidates = 0
        def _prune_stale(ts):
            stale_before = ts - timedelta(seconds=2)
            for item in list(self.aircraft_repo.all()):
                if item.ingested_utc < stale_before:
                    self.aircraft_repo.remove(item.callsign)

        def _emit_snapshot(ts):
            nonlocal pending_alerts, pending_candidates
            snapshot = EngineSnapshot(
                frame_index=len(all_snapshots),
                timestamp_utc=ts.isoformat(),
                candidate_pairs=pending_candidates,
                new_alerts=pending_alerts,
                aircraft_count=len(self.aircraft_repo.all()),
                total_alerts=len(alerts),
                aircraft=[self._aircraft_snapshot(item) for item in self.aircraft_repo.all()],
            )
            all_snapshots.append(snapshot)
            pending_alerts = []
            pending_candidates = 0

        for frame_index, frame in enumerate(frames):
            FRAME_COUNT.inc()
            frame_time = frame.timestamp_utc.astimezone(timezone.utc)

            if last_snapshot_time is None:
                last_snapshot_time = frame_time
            elif frame_time != last_snapshot_time:
                # Run scan for the completed tick, then snapshot.
                _prune_stale(last_snapshot_time)
                candidates = self.thread1.process_states(
                    self.aircraft_repo.all(),
                    frame_timestamp_utc=last_snapshot_time,
                    flight_plans=self._flight_plans,
                    state_histories=self._state_history,
                )
                pending_candidates = len(candidates)
                for candidate in candidates:
                    alert_a = await self.thread2a.consume(candidate)
                    if alert_a is not None:
                        alerts.append(alert_a)
                        row_id = len(self.audit_repo.rows)
                        self._alert_row_index[alert_a.alert_id] = row_id
                        self._row_to_frame_index[row_id] = len(all_snapshots)
                        frame_alert = self._serialize_alert(alert_a)
                        frame_alert["row_id"] = row_id
                        pending_alerts.append(frame_alert)
                    alert_b = await self.thread2b.consume(candidate)
                    if alert_b is not None:
                        alerts.append(alert_b)
                        row_id = len(self.audit_repo.rows)
                        self._alert_row_index[alert_b.alert_id] = row_id
                        self._row_to_frame_index[row_id] = len(all_snapshots)
                        frame_alert = self._serialize_alert(alert_b)
                        frame_alert["row_id"] = row_id
                        pending_alerts.append(frame_alert)

                _emit_snapshot(last_snapshot_time)
                last_snapshot_time = frame_time

            with FRAME_PROCESSING_SECONDS.time():
                with traced_span(
                    "engine.frame.ingest",
                    attributes={"frame.index": str(frame_index), "frame.timestamp_utc": frame_time.isoformat()},
                ):
                    state = self.frame_to_state(frame)
                    envelope = AircraftStateEnvelope(
                        callsign=state.normalized_callsign(),
                        state=state,
                        source=frame.source,
                        ingested_utc=frame_time,
                    )
                    self.aircraft_repo.upsert(envelope)
                    history = self._state_history.setdefault(state.normalized_callsign(), deque(maxlen=max_history))
                    history.append((frame_time, state))
                    ACTIVE_AIRCRAFT.set(len(self.aircraft_repo.all()))

        if last_snapshot_time is not None:
            _prune_stale(last_snapshot_time)
            candidates = self.thread1.process_states(
                self.aircraft_repo.all(),
                frame_timestamp_utc=last_snapshot_time,
                flight_plans=self._flight_plans,
                state_histories=self._state_history,
            )
            pending_candidates = len(candidates)
            for candidate in candidates:
                alert_a = await self.thread2a.consume(candidate)
                if alert_a is not None:
                    alerts.append(alert_a)
                    row_id = len(self.audit_repo.rows)
                    self._alert_row_index[alert_a.alert_id] = row_id
                    self._row_to_frame_index[row_id] = len(all_snapshots)
                    frame_alert = self._serialize_alert(alert_a)
                    frame_alert["row_id"] = row_id
                    pending_alerts.append(frame_alert)
                alert_b = await self.thread2b.consume(candidate)
                if alert_b is not None:
                    alerts.append(alert_b)
                    row_id = len(self.audit_repo.rows)
                    self._alert_row_index[alert_b.alert_id] = row_id
                    self._row_to_frame_index[row_id] = len(all_snapshots)
                    frame_alert = self._serialize_alert(alert_b)
                    frame_alert["row_id"] = row_id
                    pending_alerts.append(frame_alert)

            _emit_snapshot(last_snapshot_time)

        if max_snapshots is not None:
            visible_snapshots = all_snapshots[-max_snapshots:]
        else:
            visible_snapshots = all_snapshots

        self._last_snapshots = all_snapshots
        self._logger.info(
            "engine.run_with_history.done",
            frames_processed=len(all_snapshots),
            alerts_emitted=len(alerts),
        )
        return alerts, visible_snapshots

    def health(self) -> dict[str, int]:
        ACTIVE_AIRCRAFT.set(len(self.aircraft_repo.all()))
        return {
            "aircraft": len(self.aircraft_repo.all()),
            "alerts": len(self.audit_repo.rows),
            "grid_cells": self.thread1._grid.occupied_cells(),
        }
