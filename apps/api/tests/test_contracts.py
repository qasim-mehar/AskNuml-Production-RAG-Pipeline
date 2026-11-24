"""Core round-trip and re-export contracts (L2, L12, L14)."""

from fastapi.testclient import TestClient
from helpers import make_query

from uni_rag_api import schemas as api_schemas
from uni_rag_api.fixtures import EN_ANSWER
from uni_rag_core import Answer, Citation, ImageRef, Language, Query


def test_api_schemas_reexport_core_models_without_redefining_them() -> None:
    """Identity checks prove the frozen contracts are reused, not copied."""
    assert api_schemas.Query is Query
    assert api_schemas.Answer is Answer
    assert api_schemas.Language is Language
    assert api_schemas.Citation is Citation
    assert api_schemas.ImageRef is ImageRef


def test_request_and_response_round_trip_through_core_schemas(client: TestClient) -> None:
    """Wire JSON validates against the frozen core models on both sides."""
    payload = make_query()
    Query.model_validate(payload)

    response = client.post("/api/v1/query", json=payload)
    answer = Answer.model_validate(response.json())

    assert answer == EN_ANSWER
    assert Answer.model_validate_json(response.text) == EN_ANSWER


def test_shared_contract_suite_stays_green() -> None:
    """A smoke assertion that frozen core models remain importable here."""
    assert Query.model_config["frozen"] is True
    assert Answer.model_config["frozen"] is True
    assert EN_ANSWER.model_config["frozen"] is True
