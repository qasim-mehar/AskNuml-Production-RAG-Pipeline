"""ADR 0009 feedback contract: validate, echo 202, log, persist nothing (L10, L11, L12)."""

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _post(client: TestClient, payload: dict[str, Any]) -> Any:
    return client.post("/api/v1/feedback", json=payload)


def test_valid_feedback_echoes_payload_with_trace_headers(
    client: TestClient, feedback_payloads: dict[str, Any]
) -> None:
    """A valid payload is echoed verbatim with both trace headers."""
    payload = feedback_payloads["valid"]

    response = _post(client, payload)

    assert response.status_code == 202
    assert response.json() == {**payload, "reason": None, "query_id": None}
    assert response.headers["x-request-id"]
    assert response.headers["X-Trace-Id"] == response.headers["x-request-id"]


def test_feedback_echoes_explicit_null_optionals(
    client: TestClient, feedback_payloads: dict[str, Any]
) -> None:
    """ADR 0009 echoes the validated payload, including explicit nulls."""
    payload = feedback_payloads["explicit_nulls"]

    response = _post(client, payload)

    assert response.status_code == 202
    assert response.json() == payload


def test_feedback_logs_one_structured_line_with_trace_id(
    client: TestClient, feedback_payloads: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """The log line carries answer id, sentiment, presence flags and the trace id."""
    payload = feedback_payloads["with_reason"]
    with caplog.at_level(logging.INFO, logger="uni_rag_api"):
        response = _post(client, payload)

    records = [r for r in caplog.records if r.message == "feedback.received"]
    assert len(records) == 1
    assert records[0].extra_fields["answer_id"] == payload["answer_id"]
    assert records[0].extra_fields["sentiment"] == "negative"
    assert records[0].extra_fields["reason_present"] is True
    assert records[0].extra_fields["query_id_present"] is True
    assert records[0].trace_id == response.headers["x-request-id"]


@pytest.mark.parametrize("case", ["invalid_sentiment", "missing_answer_id", "unknown_field"])
def test_invalid_feedback_returns_typed_422(
    client: TestClient, feedback_payloads: dict[str, Any], case: str
) -> None:
    """Bad sentiment, a missing answer id and unknown fields are rejected typed."""
    response = _post(client, feedback_payloads[case])

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_feedback_persists_nothing(client: TestClient, feedback_payloads: dict[str, Any]) -> None:
    """No store port is touched: object-store contents are unchanged."""
    store = client.app.state.object_store
    before = {key: store.get(key) for key in store._objects}

    response = _post(client, feedback_payloads["valid"])

    assert response.status_code == 202
    assert {key: store.get(key) for key in store._objects} == before


@pytest.mark.parametrize("case", ["with_reason", "roman_urdu"])
def test_feedback_round_trips_urdu_payloads_without_mojibake(
    client: TestClient, feedback_payloads: dict[str, Any], case: str
) -> None:
    """Urdu and Roman Urdu reasons survive the new route as raw UTF-8 (L7)."""
    payload = feedback_payloads[case]

    response = _post(client, payload)

    assert response.status_code == 202
    assert "\\u" not in response.text
    assert response.json()["reason"] == payload["reason"]
