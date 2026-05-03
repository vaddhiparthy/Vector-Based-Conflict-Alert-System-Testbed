# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Typed settings for deterministic vCAS runtime behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
import os
from pathlib import Path

import re
import yaml


def _load_dotenv(path: str = ".env") -> None:
    """Load key/value pairs from a local .env file without external dependencies.

    The working directory may differ when the service is launched from scripts or
    shortcuts, so look for `.env` relative to both the process CWD and the repo
    root.
    """

    candidates = [
        Path(path),
        Path.cwd() / path,
        Path(__file__).resolve().parents[3] / path,  # project root (src/vcas/config/.. / ..)
    ]
    env_file = next((candidate for candidate in candidates if candidate.exists()), None)
    if env_file is None:
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        value = re.sub(r"\s+#.*$", "", value).strip()
        if key not in os.environ:
            os.environ[key] = value


_load_dotenv()


TaskMode = Literal["synthetic", "replay", "simulator"]


def _load_yaml(path_var: str, default: dict[str, object]) -> dict[str, object]:
    path = os.getenv(path_var)
    if not path:
        return dict(default)
    yaml_path = Path(path)
    if not yaml_path.exists():
        return dict(default)
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return dict(default)
    merged = dict(default)
    merged.update({k: v for k, v in raw.items() if v is not None})
    return merged


def _coerce_mode(value: str) -> TaskMode:
    value = (value or "").strip().lower()
    if value in {"synthetic", "replay", "simulator"}:
        return value  # type: ignore[return-value]
    return "synthetic"


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _env_float_alias(names: tuple[str, ...], default: float) -> float:
    for name in names:
        value = os.getenv(name)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except ValueError:
            continue
    return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_datetime(name: str, default: datetime) -> datetime:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    parsed = value
    if parsed.endswith("Z"):
        parsed = parsed[:-1] + "+00:00"
    return datetime.fromisoformat(parsed).astimezone(timezone.utc)


@dataclass(frozen=True)
class Settings:
    """Centralized environment settings with conservative defaults."""

    debug: bool
    log_level: str
    source_mode: TaskMode
    scenario_path: str
    rate_hz: int

    cell_size_m: float
    protected_radius_m: float
    protected_height_m: float
    t_thread1_s: float
    t_thread2a_s: float
    persistent_close_sec: int
    alert_cooldown_s: float

    w_fp: float
    w_phys: float
    w_ml: float
    ml_enabled: bool
    ml_service_url: str
    ml_timeout_s: float
    ml_circuit_failure_threshold: int
    ml_circuit_open_seconds: float

    redis_url: str
    postgres_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str

    opensky_username: str
    opensky_password: str
    replay_airport: str
    replay_start_utc: datetime
    replay_duration_s: int
    replay_cache_root: str
    cesium_token: str
    telegram_token: str
    openweather_api_key: str

    flight_plan_window_s: int
    wind_profile_path: str

    aerodrome_lat: float
    aerodrome_lon: float
    aerodrome_alt_m: float

    @classmethod
    def from_env(cls) -> "Settings":
        surveillance_cfg = _load_yaml("VCAS_SURVEILLANCE_CONFIG", {})
        return cls(
            debug=_env_bool("VCAS_DEBUG", False),
            log_level=os.getenv("VCAS_LOG_LEVEL", "INFO"),
            source_mode=_coerce_mode(os.getenv("VCAS_SOURCE_MODE", str(surveillance_cfg.get("source_mode", "synthetic")))),
            scenario_path=os.getenv("VCAS_SCENARIO_PATH", str(surveillance_cfg.get("scenario_path", "scenarios/canonical/head_on.yml"))),
            rate_hz=_env_int("VCAS_SURVEILLANCE_RATE_HZ", 1),
            cell_size_m=_env_float("VCAS_CELL_SIZE_M", 4000.0),
            protected_radius_m=_env_float("VCAS_PROTECTED_RADIUS_M", 1852.0),
            protected_height_m=_env_float("VCAS_PROTECTED_HEIGHT_M", 609.6),
            t_thread1_s=_env_float("VCAS_THREAD1_T_TC_S", 900.0),
            t_thread2a_s=_env_float("VCAS_THREAD2A_T_TC_S", 300.0),
            persistent_close_sec=_env_int("VCAS_PERSISTENT_CLOSE_SECONDS", 15),
            alert_cooldown_s=_env_float("VCAS_ALERT_COOLDOWN_S", 20.0),
            w_fp=_env_float_alias(("VCAS_P_FP_WEIGHT", "VCAS_P_FLOPLAN_WEIGHT"), 0.20),
            w_phys=_env_float("VCAS_P_PHYS_WEIGHT", 0.30),
            w_ml=_env_float("VCAS_P_ML_WEIGHT", 0.50),
            ml_enabled=_env_bool("VCAS_ML_ENABLED", False),
            ml_service_url=os.getenv("VCAS_ML_SERVICE_URL", "http://localhost:8080/predictions/vcas-lstm"),
            ml_timeout_s=_env_float("VCAS_ML_TIMEOUT_S", 1.2),
            ml_circuit_failure_threshold=_env_int("VCAS_ML_CIRCUIT_FAILURE_THRESHOLD", 3),
            ml_circuit_open_seconds=_env_float("VCAS_ML_CIRCUIT_OPEN_SECONDS", 30.0),
            redis_url=os.getenv("VCAS_REDIS_URL", "redis://localhost:6379/0"),
            postgres_url=os.getenv("VCAS_POSTGRES_URL", "postgresql+psycopg://vcas:vcas@localhost:5432/vcas"),
            minio_endpoint=os.getenv("VCAS_MINIO_ENDPOINT", "localhost:9000"),
            minio_access_key=os.getenv("VCAS_MINIO_ACCESS_KEY", ""),
            minio_secret_key=os.getenv("VCAS_MINIO_SECRET_KEY", ""),
            opensky_username=os.getenv("VCAS_OPENSKY_USERNAME", ""),
            opensky_password=os.getenv("VCAS_OPENSKY_PASSWORD", ""),
            replay_airport=os.getenv("VCAS_REPLAY_AIRPORT", str(surveillance_cfg.get("replay_airport", "KAZO"))),
            replay_start_utc=_env_datetime(
                "VCAS_REPLAY_START_UTC",
                _coerce_datetime(str(surveillance_cfg.get("replay_start_utc", ""))),
            ),
            replay_duration_s=_env_int("VCAS_REPLAY_DURATION_S", int(surveillance_cfg.get("replay_duration_s", 3600))),
            replay_cache_root=os.getenv("VCAS_REPLAY_CACHE_ROOT", str(surveillance_cfg.get("replay_cache_root", "cache/opensky"))),
            flight_plan_window_s=_env_int("VCAS_FLIGHT_PLAN_WINDOW_S", 30),
            wind_profile_path=os.getenv("VCAS_WIND_PROFILE", "config/wind.yaml"),
            cesium_token=os.getenv("VCAS_CESIUM_TOKEN", ""),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            openweather_api_key=os.getenv("OPENWEATHER_API_KEY", ""),
            aerodrome_lat=_env_float("VCAS_AERODROME_LAT", 42.2343889),
            aerodrome_lon=_env_float("VCAS_AERODROME_LON", -85.5515556),
            aerodrome_alt_m=_env_float("VCAS_AERODROME_ALT_M", 100.0),
        )


def _coerce_datetime(value: str) -> datetime:
    if not value:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
    parsed = value
    if parsed.endswith("Z"):
        parsed = parsed[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(parsed).astimezone(timezone.utc)
    except ValueError:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
