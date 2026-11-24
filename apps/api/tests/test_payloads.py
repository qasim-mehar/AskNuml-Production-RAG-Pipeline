"""Multilingual, abstention and provenance payloads (L5, L6, L7, L12)."""

from fastapi.testclient import TestClient
from helpers import expected_body, make_query

from uni_rag_api.fixtures import (
    ABSTAIN_ANSWER,
    FALLBACK_ANSWER,
    IMAGE_ANSWER,
    QUERY_ABSTAIN,
    QUERY_IMAGE,
    QUERY_ROMAN_UR,
    QUERY_UR,
    ROMAN_UR_ANSWER,
    UR_ANSWER,
)
from uni_rag_core import Language


def test_urdu_payload_round_trips_without_mojibake(client: TestClient) -> None:
    """Urdu bytes survive request and response unchanged."""
    payload = make_query(text=QUERY_UR, query_id="query-ur-001", language=Language.UR)
    response = client.post("/api/v1/query", json=payload)

    assert response.status_code == 200
    assert response.text == expected_body(UR_ANSWER)
    assert len(response.json()["text"]) == len(UR_ANSWER.text)
    assert "\\u" not in response.text


def test_roman_urdu_payload_round_trips(client: TestClient) -> None:
    """Roman Urdu is a first-class language value, not a fallback."""
    payload = make_query(
        text=QUERY_ROMAN_UR,
        query_id="query-roman-001",
        language=Language.ROMAN_URDU,
    )
    response = client.post("/api/v1/query", json=payload)

    assert response.status_code == 200
    assert response.text == expected_body(ROMAN_UR_ANSWER)
    assert response.json()["language"] == "roman_urdu"


def test_abstaining_answer_has_next_step_and_is_never_empty(client: TestClient) -> None:
    """Weak evidence yields an explicit abstention, not an empty 200."""
    response = client.post(
        "/api/v1/query",
        json=make_query(text=QUERY_ABSTAIN, query_id="query-abstain-001"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["abstained"] is True
    assert "Next step" in body["text"]
    assert body["text"] == ABSTAIN_ANSWER.text
    assert body["citations"] == []


def test_image_references_keep_their_provenance(client: TestClient) -> None:
    """ImageRef fields from the fixture are returned untouched (L5, L6)."""
    response = client.post(
        "/api/v1/query",
        json=make_query(text=QUERY_IMAGE, query_id="query-image-001"),
    )

    assert response.status_code == 200
    assert response.json() == IMAGE_ANSWER.model_dump(mode="json")


def test_unknown_query_abstains_with_next_step(client: TestClient) -> None:
    """The fake backend never invents an answer for an unknown query (L13)."""
    response = client.post(
        "/api/v1/query",
        json=make_query(text="tell me something unknown", query_id="query-unknown-001"),
    )

    body = response.json()
    assert body["abstained"] is True
    assert "Next step" in body["text"]
    assert body["text"] == FALLBACK_ANSWER.text
