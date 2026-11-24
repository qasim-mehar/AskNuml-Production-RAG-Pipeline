"""Structured JSON logging with trace ids (L10).

No ``print`` calls exist anywhere in the repository. Every log record carries
the active trace id from a :class:`contextvars.ContextVar`.
"""

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, TextIO
from uuid import uuid4

_trace_id: ContextVar[str] = ContextVar("uni_rag_trace_id", default="")


def new_trace_id() -> str:
    """Return a fresh 32-character hexadecimal trace id."""
    return uuid4().hex


@contextmanager
def trace(trace_id: str | None = None) -> Iterator[str]:
    """Bind a trace id to the current context for the duration of the block."""
    token = _trace_id.set(trace_id or new_trace_id())
    try:
        yield _trace_id.get()
    finally:
        _trace_id.reset(token)


def current_trace_id() -> str:
    """Return the trace id bound to the current context (empty string if none)."""
    return _trace_id.get()


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "") or current_trace_id(),
        }
        extra: dict[str, Any] = getattr(record, "extra_fields", {})
        payload.update(extra)
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_logging(level: str = "INFO", *, stream: TextIO | None = None) -> None:
    """Configure the root logger with a single JSON handler."""
    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())


class TraceLogger:
    """Thin wrapper that injects the trace id and extra fields into every log."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _log(self, level: int, message: str, **extra: Any) -> None:
        self._logger.log(
            level,
            message,
            extra={"trace_id": current_trace_id(), "extra_fields": extra},
        )

    def debug(self, message: str, **extra: Any) -> None:
        """Log at DEBUG."""
        self._log(logging.DEBUG, message, **extra)

    def info(self, message: str, **extra: Any) -> None:
        """Log at INFO."""
        self._log(logging.INFO, message, **extra)

    def warning(self, message: str, **extra: Any) -> None:
        """Log at WARNING."""
        self._log(logging.WARNING, message, **extra)

    def error(self, message: str, **extra: Any) -> None:
        """Log at ERROR."""
        self._log(logging.ERROR, message, **extra)


def get_logger(name: str) -> TraceLogger:
    """Return a trace-aware logger for ``name``."""
    return TraceLogger(logging.getLogger(name))
