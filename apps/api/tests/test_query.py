"""Contract behaviours of POST /api/v1/query under fakes (L3, L11, L12)."""

import pytest
from fastapi.testclient import TestClient
from helpers import expected_body, make_query, make_settings

from uni_rag_api.app import create_app
from uni_rag_api.fixtures import EN_ANSWER, QUERY_EN


def test_query_returns_exact_fixture_answer_body(client: TestClient) -> None:
    """The response bytes are the fixture Answer, byte for byte."""
    response = client.post("/api/v1/query", json=make_query())

    assert response.status_code == 200
    assert response.text == expected_body(EN_ANSWER)


def test_query_within_top_k_ceiling_succeeds(client: TestClient) -> None:
    """A top_k equal to the typed maximum is accepted."""
    response = client.post("/api/v1/query", json=make_query(top_k=20))

    assert response.status_code == 200
    assert response.json()["answer_id"] == EN_ANSWER.answer_id


def test_top_k_above_typed_ceiling_returns_typed_422(client: TestClient) -> None:
    """The settings-driven override is enforced with a typed error body."""
    response = client.post("/api/v1/query", json=make_query(top_k=21))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "top_k must not exceed 20."
    assert body["details"] == {"top_k": 21, "max_top_k": 20}


def test_malformed_body_returns_typed_422(client: TestClient) -> None:
    """Framework validation is mapped into the shared error envelope."""
    response = client.post("/api/v1/query", json={"text": QUERY_EN})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "Request validation failed."


def test_unknown_route_returns_typed_404(client: TestClient) -> None:
    """Framework 404s keep the same typed error shape."""
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.parametrize("provided_key", [None, "wrong-key"])
def test_auth_stub_rejects_missing_or_wrong_key(provided_key: str | None) -> None:
    """Auth enforcement is optional but constant-time when enabled."""
    settings = make_settings(auth_enabled=True, api_key="correct-key", rate_limit_capacity=1000)
    client = TestClient(create_app(settings))
    headers = {"X-API-Key": provided_key} if provided_key is not None else None

    response = client.post("/api/v1/query", json=make_query(), headers=headers)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_auth_stub_accepts_configured_key() -> None:
    """The exact configured key passes the stub."""
    settings = make_settings(auth_enabled=True, api_key="correct-key", rate_limit_capacity=1000)
    client = TestClient(create_app(settings))

    response = client.post(
        "/api/v1/query",
        json=make_query(),
        headers={"X-API-Key": "correct-key"},
    )

    assert response.status_code == 200
    assert response.json() == EN_ANSWER.model_dump(mode="json")
