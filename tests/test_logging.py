"""Structured logs carry trace ids (L10)."""

import io
import json
import logging

from uni_rag_core import configure_logging, current_trace_id, get_logger, trace


def test_logger_output_includes_trace_id() -> None:
    buffer = io.StringIO()
    configure_logging("INFO", stream=buffer)
    try:
        with trace("trace-abc123") as active:
            assert current_trace_id() == active
            get_logger("test").info("answer generated", query_id="q-1")
        line = buffer.getvalue().strip().splitlines()[-1]
        payload = json.loads(line)
        assert payload["trace_id"] == "trace-abc123"
        assert payload["message"] == "answer generated"
        assert payload["query_id"] == "q-1"
        assert payload["level"] == "INFO"
        assert "timestamp" in payload
    finally:
        configure_logging("INFO")


def test_trace_resets_after_block() -> None:
    configure_logging("INFO", stream=io.StringIO())
    try:
        with trace("inner"):
            assert current_trace_id() == "inner"
        assert current_trace_id() == ""
    finally:
        logging.getLogger().handlers.clear()
        configure_logging("INFO")
