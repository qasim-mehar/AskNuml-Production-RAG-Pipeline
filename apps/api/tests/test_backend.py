"""Backend flag and ADR 0007 provenance pass-through (L2, L4, L5, L7, L8, L14)."""

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from helpers import expected_body, make_query

from uni_rag_api.app import create_app
from uni_rag_api.composition import Backend, PipelinePorts, resolve_backend
from uni_rag_api.fixtures import LAST_CRAWLED
from uni_rag_core import Answer, ApiSection, FakeObjectStore, ProvidersSection, Settings
from uni_rag_indexing.adapters.postgres_metadata_store import PostgresMetadataStore


def test_fake_backend_is_the_ci_default(settings: Settings) -> None:
    """With live providers off the composed backend is fake (L4, ADR 0008)."""
    assert resolve_backend(settings) is Backend.FAKE

    app = create_app(settings)
    assert app.state.backend is Backend.FAKE


def test_live_flag_selects_the_real_backend() -> None:
    """The settings-derived flag flips to real when live providers are enabled."""
    # A minimal stub pins the mapping without constructing a live Settings in
    # CI, where the core guard correctly refuses one (ADR 0008).
    settings = cast("Settings", SimpleNamespace(providers=ProvidersSection(live_enabled=True)))

    assert resolve_backend(settings) is Backend.REAL


def test_real_composition_with_injected_fakes_wires_the_pipeline(
    settings: Settings, pipeline_ports: PipelinePorts
) -> None:
    """Lane E's public pipeline runs behind the flag with only core fakes."""
    app = create_app(settings, backend=Backend.REAL, pipeline_ports=pipeline_ports)

    assert app.state.backend is Backend.REAL
    with TestClient(app) as client:
        response = client.post("/api/v1/query", json=make_query())

    assert response.status_code == 200
    answer = Answer.model_validate(response.json())
    assert answer.query_id == "query-en-001"
    assert answer.language.value == "en"


def test_live_flag_selects_the_persisted_postgres_papers_store(
    settings: Settings, pipeline_ports: PipelinePorts
) -> None:
    """ADR 0011: live mode reads Lane D's Postgres store, never a seeded fake (L3)."""
    live_settings = settings.model_copy(update={"providers": ProvidersSection(live_enabled=True)})
    app = create_app(
        live_settings,
        backend=Backend.REAL,
        pipeline_ports=pipeline_ports,
        object_store=FakeObjectStore(),
    )

    assert isinstance(app.state.paper_record_store, PostgresMetadataStore)


def test_real_backend_answer_carries_provenance_fields_byte_for_byte(
    real_app: FastAPI, real_backend_answer: Answer
) -> None:
    """last_crawled, image_url and next_step survive the HTTP boundary (L5)."""
    with TestClient(real_app) as client:
        response = client.post("/api/v1/query", json=make_query())

    assert response.status_code == 200
    assert response.text == expected_body(real_backend_answer)
    body = response.json()
    assert body["citations"][0]["last_crawled"] == LAST_CRAWLED.isoformat().replace("+00:00", "Z")
    assert body["images"][0]["image_url"] == "/api/images/images/papers/2024-p1.png"


def test_real_backend_stream_ends_with_the_full_cited_answer(real_app: FastAPI) -> None:
    """SSE's final event does not strip ADR 0007 fields either."""
    with TestClient(real_app) as client:
        response = client.post("/api/v1/query/stream", json=make_query())

    assert response.status_code == 200
    assert "\\u" not in response.text
    assert '"last_crawled":"2026-01-15T09:30:00Z"' in response.text
    assert '"image_url":"/api/images/images/papers/2024-p1.png"' in response.text


def test_real_backend_error_path_is_typed(real_app: FastAPI) -> None:
    """The new flag does not change typed error mapping."""
    with TestClient(real_app) as client:
        response = client.get("/api/images/images/papers/missing.png")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_feedback_and_images_are_traced_on_the_real_backend(real_app: FastAPI) -> None:
    """New routes bind the same trace context as queries (L10)."""
    with TestClient(real_app) as client:
        feedback = client.post(
            "/api/v1/feedback",
            json={"answer_id": "answer-real-001", "sentiment": "positive"},
            headers={"X-Trace-Id": "real-trace-1"},
        )
        image = client.get("/api/images/images/papers/2024-p1.png")

    assert feedback.status_code == 202
    assert feedback.headers["x-request-id"] == "real-trace-1"
    assert image.headers["x-request-id"]


@pytest.mark.skip(reason="live providers need SDK credentials; CI stays on fakes (ADR 0008)")
def test_live_provider_composition_requires_injected_adapters() -> None:
    """Marked, not exercised: live mode must fail loudly rather than fake silently."""
    settings = Settings.model_construct(
        api=ApiSection(), providers=ProvidersSection(live_enabled=True)
    )
    app = create_app(settings, backend=Backend.REAL)

    assert app.state.backend is Backend.REAL


def test_default_create_app_stays_env_free() -> None:
    """Embedding the app without settings keeps the deterministic fake default."""
    app = create_app()

    assert app.state.backend is Backend.FAKE
