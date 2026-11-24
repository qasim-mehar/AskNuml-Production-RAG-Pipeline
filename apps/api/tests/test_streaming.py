"""SSE streaming contract (L4, L5, L6, L7, L12)."""

from fastapi.testclient import TestClient
from helpers import make_query, parse_sse

from uni_rag_api.fixtures import (
    ABSTAIN_ANSWER,
    EN_ANSWER,
    QUERY_ABSTAIN,
    QUERY_EN,
    QUERY_UR,
    UR_ANSWER,
)


def test_stream_emits_ordered_tokens_then_matching_citations(client: TestClient) -> None:
    """Tokens preserve order and the final event carries the fixture answer."""
    response = client.post("/api/v1/query/stream", json=make_query())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(response.text)
    assert [event for event, _ in events[:-1]] == ["token"] * len(EN_ANSWER.text.split(" "))
    assert events[-1][0] == "citations"

    tokens = [data["token"] for event, data in events if event == "token"]
    assert tokens == EN_ANSWER.text.split(" ")
    assert " ".join(tokens) == EN_ANSWER.text
    assert events[-1][1]["answer"] == EN_ANSWER.model_dump(mode="json")
    assert events[-1][1]["answer"]["citations"] == EN_ANSWER.model_dump(mode="json")["citations"]


def test_stream_preserves_urdu_bytes(client: TestClient) -> None:
    """Urdu tokens arrive unescaped and join back to the original text."""
    payload = make_query(text=QUERY_UR, query_id="query-ur-001", language="ur")
    response = client.post("/api/v1/query/stream", json=payload)

    assert response.status_code == 200
    assert UR_ANSWER.text in response.text
    assert "\\u" not in response.text

    events = parse_sse(response.text)
    tokens = [data["token"] for event, data in events if event == "token"]
    assert " ".join(tokens) == UR_ANSWER.text
    assert events[-1][1]["answer"]["language"] == "ur"


def test_stream_of_abstention_ends_with_abstaining_answer(client: TestClient) -> None:
    """An abstaining stream still terminates with a cited-event answer body."""
    payload = make_query(text=QUERY_ABSTAIN, query_id="query-abstain-001")
    response = client.post("/api/v1/query/stream", json=payload)

    events = parse_sse(response.text)
    final_answer = events[-1][1]["answer"]
    assert events[-1][0] == "citations"
    assert final_answer["abstained"] is ABSTAIN_ANSWER.abstained
    assert "Next step" in final_answer["text"]


def test_stream_rejects_top_k_override(client: TestClient) -> None:
    """Streaming shares the same typed validation as the unary endpoint."""
    response = client.post("/api/v1/query/stream", json=make_query(top_k=9999, text=QUERY_EN))

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
