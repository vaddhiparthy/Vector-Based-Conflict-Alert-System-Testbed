# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Thread 2B developing-conflict loop."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from ..core.state import AlertRecord, ConflictCandidate
from ..core.event_bus import AsyncEventBus
from ..geo.coords import EnuConverter
from ..risk.composite import bucket_for, composite_probability
from ..risk.flight_path import p_fp
from ..risk.ml_client import build_feature_matrix, p_ml
from ..risk.physics import p_phys
from ..config.settings import Settings
from ..storage.repositories import AuditRepo
from ..observability import (
    ALERT_COUNT,
    THREAD2B_INPUTS,
    THREAD2B_PROCESS_SECONDS,
    THREAD2B_COUNT,
    get_logger,
    traced_span,
)


@dataclass
class Thread2BWorker:
    settings: Settings
    output_bus: AsyncEventBus[AlertRecord] | None
    audit_repo: AuditRepo
    converter: EnuConverter | None = None
    _last_emit_utc: dict[str, float] = None  # type: ignore[assignment]
    _logger = get_logger("vcas.thread2b")

    def __post_init__(self) -> None:
        self._persistent: dict[str, int] = defaultdict(int)

    async def consume(self, candidate: ConflictCandidate) -> AlertRecord | None:
        if self._last_emit_utc is None:
            self._last_emit_utc = {}
        with THREAD2B_PROCESS_SECONDS.time():
            with traced_span("thread2b.consume", attributes={"pair": "|".join(candidate.pair)}):
                THREAD2B_INPUTS.inc()
                key = "|".join(candidate.pair)
                tc = candidate.time_to_conflict_s or 0.0
                d_min = candidate.min_sep_m or 0.0
                phys = p_phys(d_min, self.settings.protected_radius_m, tc)
                converter = self.converter
                if converter is None:
                    raise RuntimeError("Thread2BWorker.converter is required for flight-plan risk scoring")
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
                if tc < self.settings.t_thread1_s and total > 0.15:
                    self._persistent[key] = self._persistent[key] + 1
                else:
                    self._persistent[key] = 0

                if self._persistent[key] >= self.settings.persistent_close_sec and tc < 600.0:
                    now_ts = float(candidate.created_utc.timestamp())
                    last = float(self._last_emit_utc.get(key, -1e18))
                    if now_ts - last < float(self.settings.alert_cooldown_s):
                        return None
                    alert = AlertRecord(
                        alert_id=f"dev_{key}_{int(datetime.utcnow().timestamp())}",
                        pair=candidate.pair,
                        created_utc=candidate.created_utc,
                        thread_state="thread2b",
                        risk_total=total,
                        risk_phys=phys,
                        risk_fp=fp,
                        risk_ml=ml,
                        tc_s=tc,
                        d_min_m=d_min,
                        bucket=bucket_for(total, tc_s=tc),
                        metadata={
                            "phase": "thread2b",
                            "persistent_frames": self._persistent[key],
                            "risk_mode": "deterministic" if not self.settings.ml_enabled else "ml_enabled",
                            **fp_meta,
                        },
                    )
                    ALERT_COUNT.inc()
                    THREAD2B_COUNT.inc()
                    self.audit_repo.append(alert)
                    self._last_emit_utc[key] = now_ts
                    if self.output_bus is not None:
                        await self.output_bus.publish(alert)
                    self._logger.info(
                        "thread2b.alert_emitted",
                        alert_id=alert.alert_id,
                        pair=alert.pair,
                        risk_total=alert.risk_total,
                    )
                    return alert
                return None
