# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Thread 2A imminent-conflict loop."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.event_bus import AsyncEventBus
from ..core.state import AlertRecord, ConflictCandidate
from ..geo.coords import EnuConverter
from ..risk.composite import bucket_for, composite_probability
from ..risk.flight_path import p_fp
from ..risk.ml_client import build_feature_matrix, p_ml
from ..risk.physics import p_phys
from ..storage.repositories import AuditRepo
from ..config.settings import Settings
from ..observability import (
    THREAD2A_INPUTS,
    THREAD2A_PROCESS_SECONDS,
    THREAD2A_COUNT,
    ALERT_COUNT,
    get_logger,
    traced_span,
)


@dataclass
class Thread2AWorker:
    settings: Settings
    output_bus: AsyncEventBus[AlertRecord] | None
    audit_repo: AuditRepo
    converter: EnuConverter | None = None
    _last_emit_utc: dict[tuple[str, str], float] = None  # type: ignore[assignment]
    _logger = get_logger("vcas.thread2a")

    async def consume(self, candidate: ConflictCandidate) -> AlertRecord | None:
        if self._last_emit_utc is None:
            self._last_emit_utc = {}
        with THREAD2A_PROCESS_SECONDS.time():
            with traced_span("thread2a.consume", attributes={"pair": "|".join(candidate.pair)}):
                THREAD2A_INPUTS.inc()
                d_min = candidate.min_sep_m or 0.0
                tc = candidate.time_to_conflict_s if candidate.time_to_conflict_s is not None else 1e9
                phys = p_phys(d_min, self.settings.protected_radius_m, tc)
                converter = self.converter
                if converter is None:
                    raise RuntimeError("Thread2AWorker.converter is required for flight-plan risk scoring")
                fp, fp_meta = p_fp(
                    candidate,
                    converter=converter,
                    protected_radius_m=self.settings.protected_radius_m,
                    flight_plan_window_s=self.settings.flight_plan_window_s,
                )
                ml_sequence = build_feature_matrix(candidate, sample_count=8)
                ml = float(
                    (
                        await p_ml(
                            ml_sequence,
                            service_healthy=self.settings.ml_enabled,
                            service_url=self.settings.ml_service_url,
                            timeout_s=self.settings.ml_timeout_s,
                        )
                    )[0]
                )
                total = composite_probability(
                    p_phys=phys,
                    p_fp=fp,
                    p_ml=ml,
                    w_fp=self.settings.w_fp,
                    w_phys=self.settings.w_phys,
                    w_ml=self.settings.w_ml,
                )
                mode = "deterministic" if not self.settings.ml_enabled else "ml_enabled"
                bucket = bucket_for(total, tc_s=tc)
                if tc <= self.settings.t_thread2a_s or total > 0.70:
                    key = tuple(sorted(candidate.pair))
                    now_ts = float(candidate.created_utc.timestamp())
                    last = float(self._last_emit_utc.get(key, -1e18))
                    if now_ts - last < float(self.settings.alert_cooldown_s):
                        return None
                    alert = AlertRecord(
                        alert_id=f"{candidate.pair[0]}_{candidate.pair[1]}_{int(candidate.created_utc.timestamp())}",
                        pair=candidate.pair,
                        created_utc=candidate.created_utc,
                        thread_state="thread2a",
                        risk_total=total,
                        risk_phys=phys,
                        risk_fp=fp,
                        risk_ml=ml,
                        tc_s=tc,
                        d_min_m=d_min,
                        bucket=bucket,
                        metadata={"phase": "thread2a", "risk_mode": mode, **fp_meta},
                    )
                    ALERT_COUNT.inc()
                    THREAD2A_COUNT.inc()
                    self.audit_repo.append(alert)
                    self._last_emit_utc[key] = now_ts
                    if self.output_bus is not None:
                        await self.output_bus.publish(alert)
                    self._logger.info(
                        "thread2a.alert_emitted",
                        alert_id=alert.alert_id,
                        pair=alert.pair,
                        risk_total=alert.risk_total,
                    )
                    return alert
                return None
