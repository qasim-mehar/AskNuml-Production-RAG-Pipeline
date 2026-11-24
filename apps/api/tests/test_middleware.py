"""Trace and rate-limit middleware behaviour (L8, L10, L11, L12)."""

import json
import logging
import re

import pytest
from conftest import SteppableClock
from fastapi.testclient import TestClient
from helpers import make_query, make_settings

from uni_rag_api.app import create_app
from uni_rag_core.logging.logger import JsonFormatter


def test_trace_id_is_propagated_to_header_and_json_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """An incoming trace id is echoed and bound to every request log."""
    with caplog.at_level(logging.INFO, logger="uni_rag_api"):
        response = client.get("/health/live", headers={"X-Trace-Id": "trace-abc-123"})

    assert response.headers["X-Trace-Id"] == "trace-abc-123"
    records = [record for record in caplog.records if record.name.startswith("uni_rag_api")]
    assert records
    assert all(record.trace_id == "trace-abc-123" for record in records)
    assert json.loads(JsonFormatter().format(records[0]))["trace_id"] == "trace-abc-123"


def test_trace_id_is_minted_when_absent(client: TestClient) -> None:
    """Every request gets a trace id even without an incoming header."""
    response = client.get("/health/live")

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Trace-Id"])


def test_unsafe_incoming_trace_id_is_replaced(client: TestClient) -> None:
    """Untrusted header values cannot break the header or poison logs."""
    response = client.get("/health/live", headers={"X-Trace-Id": "bad id"})

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Trace-Id"])


def test_trace_header_name_is_settings_driven() -> None:
    """The trace header name is a typed setting, not a literal."""
    client = TestClient(create_app(make_settings(trace_header="X-Custom-Trace")))

    response = client.get("/health/live")

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Custom-Trace"])


def test_trace_header_can_be_disabled_without_losing_request_id() -> None:
    """ADR 0008's trace_header_enabled switch is honoured (L8, L10)."""
    client = TestClient(create_app(make_settings(trace_header_enabled=False)))

    response = client.get("/health/live")

    assert response.headers["x-request-id"]
    assert "X-Trace-Id" not in response.headers


def test_rate_limit_returns_typed_429_and_refills_on_clock(
    clock: SteppableClock,
) -> None:
    """The bucket enforces capacity and refills at the settings-driven rate."""
    settings = make_settings(
        auth_enabled=False, rate_limit_capacity=2, rate_limit_refill_per_second=1.0
    )
    client = TestClient(create_app(settings, clock=clock))

    assert client.post("/api/v1/query", json=make_query()).status_code == 200
    assert client.post("/api/v1/query", json=make_query()).status_code == 200

    limited = client.post("/api/v1/query", json=make_query())
    assert limited.status_code == 429
    assert limited.json() == {
        "code": "rate_limited",
        "message": "Too many requests.",
        "details": {"retry_after_seconds": 1},
    }
    assert limited.headers["Retry-After"] == "1"
    assert re.fullmatch(r"[0-9a-f]{32}", limited.headers["X-Trace-Id"])

    clock.advance(1.0)
    assert client.post("/api/v1/query", json=make_query()).status_code == 200


def test_rate_limit_buckets_are_per_api_key() -> None:
    """Separate keys never share a bucket."""
    settings = make_settings(
        auth_enabled=False, rate_limit_capacity=1, rate_limit_refill_per_second=1.0
    )
    client = TestClient(create_app(settings))

    assert (
        client.post("/api/v1/query", json=make_query(), headers={"X-API-Key": "key-a"}).status_code
        == 200
    )
    assert (
        client.post("/api/v1/query", json=make_query(), headers={"X-API-Key": "key-b"}).status_code
        == 200
    )
    assert (
        client.post("/api/v1/query", json=make_query(), headers={"X-API-Key": "key-a"}).status_code
        == 429
    )


def test_health_probes_are_exempt_from_rate_limiting() -> None:
    """Probes stay available even when the query bucket is empty."""
    settings = make_settings(
        auth_enabled=False, rate_limit_capacity=1, rate_limit_refill_per_second=1.0
    )
    client = TestClient(create_app(settings))

    assert client.post("/api/v1/query", json=make_query()).status_code == 200
    for _ in range(5):
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
