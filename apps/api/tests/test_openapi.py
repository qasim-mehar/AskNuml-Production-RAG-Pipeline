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


def test_openapi_documents_query_key_auth(client: TestClient) -> None:
    """The auth stub is visible to Lane H regardless of enforcement."""
    schema = client.get("/openapi.json").json()

    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["ApiKeyAuth"]["name"] == "X-API-Key"
