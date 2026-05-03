# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""In-memory repository layer for audit-chain and pair lifecycle persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import asdict as dataclass_asdict
import dataclasses
from typing import Iterable

from ..core.state import AlertRecord, AircraftStateEnvelope


def _hash_chain_row(payload: str, prev_hash: str | None) -> str:
    base = f"{prev_hash or ''}|{payload}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()


@dataclass
class AircraftRepo:
    """Last known snapshot per callsign."""

    latest: dict[str, AircraftStateEnvelope]

    def __init__(self) -> None:
        self.latest = {}

    def upsert(self, state: AircraftStateEnvelope) -> None:
        self.latest[state.callsign] = state

    def get(self, callsign: str) -> AircraftStateEnvelope | None:
        return self.latest.get(callsign)

    def all(self) -> list[AircraftStateEnvelope]:
        return list(self.latest.values())

    def remove(self, callsign: str) -> None:
        self.latest.pop(callsign, None)


@dataclass
class ConflictRepo:
    """Mutable conflict/pair state table."""

    states: dict[tuple[str, str], dict]

    def __init__(self) -> None:
        self.states = {}

    def upsert_pair(self, pair: tuple[str, str], payload: dict) -> None:
        self.states[tuple(sorted(pair))] = dict(payload)

    def get_pair(self, a: str, b: str) -> dict | None:
        return self.states.get(tuple(sorted((a, b))))

    def snapshot(self) -> list[dict]:
        return [dict(v, pair=",".join(pair)) for pair, v in self.states.items()]


@dataclass
class AuditRepo:
    """Append-only audit ledger with hash chaining."""

    rows: list[dict]

    def __init__(self) -> None:
        self.rows = []

    @staticmethod
    def _serialize_payload(payload: object) -> dict:
        if hasattr(payload, "model_dump"):
            value = payload.model_dump()
            if isinstance(value, dict):
                return value
        if dataclasses.is_dataclass(payload):
            return dataclass_asdict(payload)
        if isinstance(payload, dict):
            return dict(payload)
        if hasattr(payload, "__dict__"):
            return dict(payload.__dict__)
        raise TypeError(f"Unsupported payload type: {type(payload)!r}")

    def append(self, alert: AlertRecord) -> dict:
        serialized = self._serialize_payload(alert)
        payload = json.dumps(serialized, sort_keys=True, default=str)
        prev_hash = self.rows[-1]["row_hash"] if self.rows else None
        row_hash = _hash_chain_row(payload, prev_hash)
        row = {
            "id": len(self.rows) + 1,
            "created_utc": alert.created_utc.isoformat(),
            "prev_hash": prev_hash,
            "row_hash": row_hash,
            "payload": serialized,
        }
        self.rows.append(row)
        return row

    def verify_chain(self) -> int | None:
        prev: str | None = None
        for idx, row in enumerate(self.rows, start=1):
            expected = _hash_chain_row(json.dumps(row["payload"], sort_keys=True, default=str), prev)
            if row["row_hash"] != expected:
                return row["id"]
            prev = row["row_hash"]
            if row["prev_hash"] != (self.rows[idx - 2]["row_hash"] if idx > 1 else None):
                return row["id"]
        return None

    def all(self) -> Iterable[dict]:
        return list(self.rows)

    def get_by_alert_id(self, alert_id: str) -> dict | None:
        for row in self.rows:
            payload = row["payload"]
            if payload.get("alert_id") == alert_id:
                return row
        return None
