"""Request-scoped observability primitives used by the production boundary.

The application keeps the default implementation dependency-free. Sentry and
OpenTelemetry are optional integrations that activate only when their
corresponding deployment settings and packages are present.
"""

from __future__ import annotations

import json
import logging
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

from app.config import settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
trip_job_id_context: ContextVar[str] = ContextVar("trip_job_id", default="-")

_tracer = None
_sentry = None


class StructuredFormatter(logging.Formatter):
    """Emit one JSON object per log record for hosted log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
            "trip_job_id": trip_job_id_context.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("metric", "provider", "duration_ms", "success", "error_code", "model", "input_tokens", "output_tokens", "total_tokens"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_observability() -> None:
    """Initialise optional telemetry integrations once during app startup."""

    global _tracer, _sentry
    root = logging.getLogger()
    if not root.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(StructuredFormatter())
        root.addHandler(stream_handler)
    else:
        for existing_handler in root.handlers:
            existing_handler.setFormatter(StructuredFormatter())
    root.setLevel(logging.INFO)

    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            _sentry = sentry_sdk
        except ImportError:
            logging.getLogger(__name__).warning("SENTRY_DSN is set but sentry-sdk is not installed")
        except Exception:
            logging.getLogger(__name__).exception("Sentry initialisation failed")

    try:
        from opentelemetry import trace

        if settings.otel_exporter_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            provider = TracerProvider(resource=Resource.create({"service.name": "yatraai-backend", "deployment.environment": settings.environment}))
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)))
            trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer("yatraai.backend")
    except ImportError:
        _tracer = None
    except Exception:
        logging.getLogger(__name__).exception("OpenTelemetry initialisation failed")
        _tracer = None


def set_request_context(request_id: str, trip_job_id: str = "-") -> tuple[Token[str], Token[str]]:
    return request_id_context.set(request_id), trip_job_id_context.set(trip_job_id)


def reset_request_context(tokens: tuple[Token[str], Token[str]]) -> None:
    request_id_context.reset(tokens[0])
    trip_job_id_context.reset(tokens[1])


@contextmanager
def request_span(name: str) -> Iterator[object]:
    """Create an OpenTelemetry span when the SDK is installed, otherwise noop."""

    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as span:
        span.set_attribute("yatraai.request_id", request_id_context.get())
        job_id = trip_job_id_context.get()
        if job_id != "-":
            span.set_attribute("yatraai.trip_job_id", job_id)
        yield span


def record_metric(name: str, **fields: object) -> None:
    """Write privacy-safe operational metrics to structured logs."""

    logging.getLogger("yatraai.metrics").info("metric", extra={"metric": name, **fields})


def record_provider_call(provider: str, duration_ms: float, *, success: bool, error_code: str | None = None) -> None:
    record_metric(
        "provider_call",
        provider=provider,
        duration_ms=round(duration_ms, 2),
        success=success,
        error_code=error_code,
    )


def record_llm_usage(model: str, duration_ms: float, response: object | None = None) -> None:
    """Record model latency and available token counts without prompt content."""

    usage = getattr(response, "usage_metadata", None)
    fields: dict[str, object] = {
        "model": model,
        "duration_ms": round(duration_ms, 2),
    }
    for source, target in (
        ("prompt_token_count", "input_tokens"),
        ("candidates_token_count", "output_tokens"),
        ("total_token_count", "total_tokens"),
    ):
        value = getattr(usage, source, None)
        if isinstance(value, int):
            fields[target] = value
    record_metric("llm_usage", **fields)


def capture_exception(error: BaseException, *, context: dict[str, object] | None = None) -> None:
    if _sentry is None:
        return
    try:
        with _sentry.push_scope() as scope:
            for key, value in (context or {}).items():
                scope.set_extra(key, value)
            _sentry.capture_exception(error)
    except Exception:
        logging.getLogger(__name__).debug("Could not report exception to Sentry", exc_info=True)


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)=([^\s&]+)"),
    re.compile(r"https?://[^\s]+"),
)


def safe_error_message(error: BaseException, fallback: str) -> str:
    """Return an API-safe error while keeping the raw exception in logs."""

    candidate = str(error).strip()
    if not candidate or len(candidate) > 240:
        return fallback
    if any(pattern.search(candidate) for pattern in _SECRET_PATTERNS):
        return fallback
    return fallback


def monotonic_ms() -> float:
    return time.perf_counter() * 1000
