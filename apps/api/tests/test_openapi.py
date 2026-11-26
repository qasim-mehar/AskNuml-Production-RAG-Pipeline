"""Committed OpenAPI artifact and schema-drift contract (L12, L14)."""

from pathlib import Path

from fastapi.testclient import TestClient

from uni_rag_core import Answer, Query

ARTIFACT = Path(__file__).resolve().parents[1] / "openapi.json"


def test_served_openapi_matches_committed_artifact_byte_for_byte(client: TestClient) -> None:
    """Lane H can rely on the committed artifact as the live contract."""
    assert ARTIFACT.is_file(), f"missing committed artifact: {ARTIFACT}"

    served = client.get("/openapi.json")

    assert served.status_code == 200
    assert served.text.encode("utf-8") == ARTIFACT.read_bytes()


def test_openapi_schemas_come_from_frozen_core_models(client: TestClient) -> None:
    """No request/response field is redefined at the API boundary."""
    schema = client.get("/openapi.json").json()
    query_schema = schema["components"]["schemas"]["Query"]
    answer_schema = schema["components"]["schemas"]["Answer"]

    assert set(query_schema["properties"]) == set(Query.model_fields)
    assert set(answer_schema["properties"]) == set(Answer.model_fields)
    assert query_schema["required"] == ["query_id", "text", "language"]


def test_openapi_documents_new_routes_and_feedback_schema(client: TestClient) -> None:
    """Lane H generates its client from this artifact (L12)."""
    schema = client.get("/openapi.json").json()

    assert "/api/v1/query" in schema["paths"]
    assert "/api/v1/query/stream" in schema["paths"]
    assert "/api/v1/feedback" in schema["paths"]
    assert "/api/images/{ref_id}" in schema["paths"]
    assert schema["paths"]["/api/v1/feedback"]["post"]["responses"]["202"]["description"]
    feedback = schema["components"]["schemas"]["FeedbackRequest"]
    assert set(feedback["properties"]) == {"answer_id", "sentiment", "reason", "query_id"}
    assert feedback["required"] == ["answer_id", "sentiment"]


def test_openapi_declares_x_request_id_on_every_operation(client: TestClient) -> None:
    """H2's residual is closed: every documented response carries trace correlation."""
    schema = client.get("/openapi.json").json()
    operations = [
        (path, method, operation)
        for path, item in schema["paths"].items()
        for method, operation in item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]

    assert len(operations) >= 7
    for path, method, operation in operations:
        assert operation["responses"], f"{method.upper()} {path} has no responses"
        for status, response in operation["responses"].items():
            header = response.get("headers", {}).get("x-request-id")
            assert header, f"{method.upper()} {path} {status} omits x-request-id"
            assert header["schema"]["type"] == "string"


def test_openapi_documents_sse_envelopes_in_the_stream_description(client: TestClient) -> None:
    """ADR 0009 keeps envelopes API-local, so their shapes live in the description."""
    schema = client.get("/openapi.json").json()
    description = schema["paths"]["/api/v1/query/stream"]["post"]["description"]

    for fragment in (
        "text/event-stream",
        "event: token",
        '{"token"',
        "TokenEvent",
        "event: citations",
        '{"answer"',
        "CitationsEvent",
        "ADR 0009",
        "ErrorBody",
    ):
        assert fragment in description


def test_openapi_documents_papers_route_with_persisted_store_label(client: TestClient) -> None:
    """Lane H gets the real papers path plus an honest data-source label."""
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/papers"]["get"]

    assert "AND" in operation["description"]
    assert "parsed-record store" in operation["description"]
    assert "ADR 0011" in operation["description"]
    assert "fixture-backed" not in operation["description"]
    assert set(operation["parameters"][i]["name"] for i in range(5)) == {
        "course_code",
        "year",
        "term",
        "exam_type",
        "department",
    }
    item_schema = schema["components"]["schemas"]["PaperRecord"]
    assert {
        "source_url",
        "page",
        "image_ref",
        "last_crawled",
        "course_code",
        "term",
        "exam_type",
        "department",
    } <= set(item_schema["properties"])
    assert set(schema["components"]["schemas"]["PaperSearchResult"]["properties"]) == {"results"}


def test_openapi_documents_query_key_auth(client: TestClient) -> None:
    """The auth stub is visible to Lane H regardless of enforcement."""
    schema = client.get("/openapi.json").json()

    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["ApiKeyAuth"]["name"] == "X-API-Key"
