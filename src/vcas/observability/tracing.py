# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Optional OpenTelemetry tracing wrappers for frame and thread workflows."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator


try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter
except Exception:  # pragma: no cover - optional dependency fallback
    trace = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]
    BatchSpanProcessor = None  # type: ignore[assignment]
    ConsoleSpanExporter = None  # type: ignore[assignment]
    SpanExporter = Any


@dataclass(frozen=True)
class _NoopSpan:
    def set_attribute(self, *_args: object, **_kwargs: object) -> None:
        return None

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def configure_tracing(service_name: str = "vcas") -> None:
    if os.getenv("VCAS_TRACING_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    if trace is None:
        return
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
    )
    trace.set_tracer_provider(provider)

    # Keep default exporter no-op unless explicitly enabled to avoid hard dependencies.
    if False:
        processor = BatchSpanProcessor(ConsoleSpanExporter())  # pragma: no cover
        provider.add_span_processor(processor)


def _otlp_exporter() -> SpanExporter | None:
    if trace is None:
        return None
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore
    except Exception:
        return None
    return OTLPSpanExporter(
        endpoint="http://jaeger:4317",
        insecure=True,
    )


def configure_otlp_exporter() -> None:
    if os.getenv("VCAS_OTLP_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    if trace is None:
        return
    exporter = _otlp_exporter()
    if exporter is None or BatchSpanProcessor is None:
        return
    provider = trace.get_tracer_provider()
    provider.add_span_processor(BatchSpanProcessor(exporter))


def tracer() -> Any:
    if trace is None:
        return _NoopSpan()
    return trace.get_tracer("vcas.core")


@contextmanager
def traced_span(name: str, *, attributes: dict[str, str] | None = None) -> Iterator[object]:
    if trace is None:
        yield _NoopSpan()
        return
    with tracer().start_as_current_span(name) as span:  # type: ignore[attr-defined]
        if attributes is not None:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


__all__ = ["configure_otlp_exporter", "configure_tracing", "traced_span"]
