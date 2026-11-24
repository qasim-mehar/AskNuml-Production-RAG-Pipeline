"""Health probes and typed error mapping (L3, L11, L12)."""

import json
import logging
import re

import pytest
from fastapi.testclient import TestClient
from helpers import make_query

from uni_rag_api.app import create_app
from uni_rag_api.config import ApiSettings
from uni_rag_api.service import FakeHealthProbe
from uni_rag_core import Answer, PortError, Query, StorageError
from uni_rag_core.logging.logger import JsonFormatter


def test_liveness_does_not_consult_ports(client: TestClient) -> None:
    """Liveness stays up even when readiness is down."""
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "uni-rag-api"}


def test_readiness_returns_503_when_injected_probe_is_unhealthy() -> None:
    """Readiness checks the injected port and maps failure to 503."""
    client = TestClient(create_app(health_probe=FakeHealthProbe(ready=False)))

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "upstream_unavailable"


def test_readiness_succeeds_with_healthy_probe(client: TestClient) -> None:
    """The default fake probe reports ready."""
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "uni-rag-api"}


def test_upstream_port_failure_maps_to_503() -> None:
    """A core PortError keeps its typed envelope and status."""

    class FailingService:
        def answer(self, query: Query) -> Answer:
            raise StorageError("vector store unavailable", context={"port": "vector_store"})

        def tokens(self, answer: Answer):  # pragma: no cover - never reached
            yield from ()

    client = TestClient(create_app(answer_service=FailingService()))

    response = client.post("/api/v1/query", json=make_query())

    assert response.status_code == 503
    assert response.json() == {
        "code": "upstream_unavailable",
        "message": "vector store unavailable",
        "details": {"port": "vector_store"},
    }


def test_unhandled_error_is_typed_and_its_cause_logged(caplog: pytest.LogCaptureFixture) -> None:
    """No handler returns a bare 500 without a typed cause in the logs."""

    class BrokenService:
        def answer(self, query: Query) -> Answer:
            msg = "unexpected adapter bug"
            raise RuntimeError(msg)

        def tokens(self, answer: Answer):  # pragma: no cover - never reached
            yield from ()

    client = TestClient(create_app(answer_service=BrokenService()), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="uni_rag_api"):
        response = client.post("/api/v1/query", json=make_query())

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "details": {},
    }
    errors = [r for r in caplog.records if r.message == "api.unhandled_error"]
    assert len(errors) == 1
    assert "RuntimeError: unexpected adapter bug" in errors[0].extra_fields["cause"]
    assert json.loads(JsonFormatter().format(errors[0]))["trace_id"]


def test_unhandled_error_echoes_configured_trace_header() -> None:
    """Even a 500 produced outside the middleware stack carries the trace id."""

    class BrokenService:
        def answer(self, query: Query) -> Answer:
            msg = "unexpected adapter bug"
            raise RuntimeError(msg)

        def tokens(self, answer: Answer):  # pragma: no cover - never reached
            yield from ()

    settings = ApiSettings(trace_header="X-Custom-Trace")
    client = TestClient(
        create_app(settings, answer_service=BrokenService()),
        raise_server_exceptions=False,
    )

    response = client.post("/api/v1/query", json=make_query())

    assert response.status_code == 500
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Custom-Trace"])


def test_port_error_without_typed_cause_is_never_silently_swallowed() -> None:
    """Core PortError is mapped explicitly rather than caught by a bare except."""
    from uni_rag_api.errors import map_error

    assert map_error(PortError("down")) == (503, "upstream_unavailable")
