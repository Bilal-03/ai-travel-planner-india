"""Request-scoped structured logging primitives used by the production boundary."""

from __future__ import annotations

import json
import logging
import re
import time
from contextvars import ContextVar, Token

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
trip_job_id_context: ContextVar[str] = ContextVar("trip_job_id", default="-")


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
    """Configure structured application logging once during app startup."""

    root = logging.getLogger()
    if not root.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(StructuredFormatter())
        root.addHandler(stream_handler)
    else:
        for existing_handler in root.handlers:
            existing_handler.setFormatter(StructuredFormatter())
    root.setLevel(logging.INFO)


def set_request_context(request_id: str, trip_job_id: str = "-") -> tuple[Token[str], Token[str]]:
    return request_id_context.set(request_id), trip_job_id_context.set(trip_job_id)


def reset_request_context(tokens: tuple[Token[str], Token[str]]) -> None:
    request_id_context.reset(tokens[0])
    trip_job_id_context.reset(tokens[1])


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
    logging.getLogger("yatraai.errors").error(
        "Unhandled application exception",
        exc_info=(type(error), error, error.__traceback__),
        extra={"error_context": context or {}},
    )


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
