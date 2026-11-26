"""Regenerate the contract fixtures from core models and the OpenAPI artifact.

Run from the repository root:
    uv run python apps/web/scripts/generate_contract_fixture.py

Two deterministic files are written to ``apps/web/src/lib/api/mocks``:

* ``core-emitted.json`` — real Pydantic core model dumps, including the optional
  ADR-0007 provenance fields, plus ``paper_record``: the core dump extended with
  the API-local ``last_crawled`` field of the artifact's ``PaperRecord`` (ADR
  0011). The Vitest mirror suite round-trips these through the TypeScript Zod
  schemas, so mirror fidelity is measured against real core output rather than
  a hand-written copy (L1).
* ``openapi-emitted.json`` — example payloads, route strings, finder filters,
  the empty result shape, error statuses and the documented trace header derived
  from ``apps/api/openapi.json`` (the served artifact). Tests assert client routes
  and response shapes against this file instead of hand-written URLs, so artifact
  drift fails the suite.

This is a development-time generator; tests never import Python or the API.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "packages" / "core" / "src"))

from uni_rag_core.schemas.answer import Answer, Citation  # noqa: E402
from uni_rag_core.schemas.chunk import ImageRef  # noqa: E402
from uni_rag_core.schemas.enums import Language  # noqa: E402
from uni_rag_core.schemas.past_paper import PastPaperQuestion  # noqa: E402
from uni_rag_core.schemas.query import Query  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "apps" / "web" / "src" / "lib" / "api" / "mocks"
OPENAPI = REPO_ROOT / "apps" / "api" / "openapi.json"

CRAWLED_AT = datetime(2026, 11, 20, 9, 30, tzinfo=UTC)

# Routes that come from binding ADRs rather than a hand-written test URL. The
# papers route is no longer a convention: G3 emitted it, so it is resolved from
# the served artifact's operationId alongside query and stream.
CONVENTIONS = {
    "feedback": "/api/v1/feedback",  # ADR 0009
    "images_prefix": "/api/images/",  # ADR 0007
}

PAPERS_OPERATION_ID = "find_papers_api_v1_papers_get"


def core_payload() -> dict[str, Any]:
    """Emit representative core model dumps for every mirrored schema."""
    query = Query(
        query_id="q-contract",
        text="What is the fee?",
        language=Language.EN,
        top_k=5,
        filters={"department": "CS"},
    )
    citation = Citation(
        chunk_id="c-1",
        doc_id="d-1",
        source_url="https://uni.example/fees",
        snippet="Fee is 1000",
        page=3,
        score=0.91,
        last_crawled=CRAWLED_AT,
    )
    image = ImageRef(
        ref_id="img-1",
        source_url="https://uni.example/past/2024",
        page=2,
        caption="Past paper page 2",
        image_url=f"{CONVENTIONS['images_prefix']}img-1",
    )
    answer = Answer(
        answer_id="a-contract",
        query_id="q-contract",
        text="The fee is 1000.",
        citations=[citation],
        images=[image],
        abstained=False,
        confidence=0.91,
        language=Language.EN,
        next_step=None,
        abstention_reason=None,
    )
    paper = PastPaperQuestion(
        question_id="pp-1",
        doc_id="d-pp",
        source_url="https://uni.example/past/2024",
        page=1,
        question_number=4,
        text="What is 2+2?",
        year=2024,
        subject="CS",
        options=["3", "4"],
        image_ref=image,
        course_code="CS",
        term="fall",
        exam_type="final",
        department="Computer Science",
    )
    abstained = Answer(
        answer_id="a-abstain",
        query_id="q-contract",
        text="Insufficient evidence; try a more specific question.",
        abstained=True,
        confidence=0.0,
        language=Language.UR,
        next_step="Search the past-paper archive for a course code.",
        abstention_reason="The retrieved chunks do not state the deadline.",
    )
    return {
        "query": json.loads(query.model_dump_json()),
        "citation": json.loads(citation.model_dump_json()),
        "image_ref": json.loads(image.model_dump_json()),
        "answer": json.loads(answer.model_dump_json()),
        "past_paper": json.loads(paper.model_dump_json()),
        # PaperRecord is API-local: PastPaperQuestion plus the frozen crawl time.
        # Core cannot emit the field, so extend its dump with the same frozen
        # timestamp used for Citation provenance (L5, ADR 0011).
        "paper_record": {
            **json.loads(paper.model_dump_json()),
            "last_crawled": CRAWLED_AT.isoformat().replace("+00:00", "Z"),
        },
        "abstained_answer": json.loads(abstained.model_dump_json()),
    }


def example_string(name: str, schema: dict[str, Any]) -> str:
    """Deterministic string example; format and field name choose the value."""
    if schema.get("format") == "date-time":
        return CRAWLED_AT.isoformat().replace("+00:00", "Z")
    if schema.get("const"):
        return str(schema["const"])
    examples = {
        "source_url": "https://uni.example/source",
        "image_url": f"{CONVENTIONS['images_prefix']}img-1",
        "answer_id": "a-artifact",
        "query_id": "q-artifact",
        "chunk_id": "c-artifact",
        "doc_id": "d-artifact",
        "ref_id": "img-artifact",
        "code": "upstream_unavailable",
        "message": "The knowledge service is temporarily unavailable.",
        "text": "The fee is 1000.",
        "snippet": "Fee is 1000",
        "next_step": "Search the past-paper archive.",
        "abstention_reason": "Evidence is insufficient.",
        "service": "uni-rag-api",
        "mime_type": "image/png",
    }
    return examples.get(name, f"{name}-artifact")


def example_from_schema(
    schema: dict[str, Any],
    components: dict[str, Any],
    name: str = "value",
) -> Any:
    """Build one deterministic example from the subset of JSON Schema we serve."""
    if "default" in schema:
        return schema["default"]
    if "$ref" in schema:
        target = schema["$ref"].rsplit("/", 1)[-1]
        return example_from_schema(components[target], components, target)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema:
        branches = [branch for branch in schema["anyOf"] if branch.get("type") != "null"]
        return example_from_schema(branches[0], components, name)
    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        return {
            key: example_from_schema(child, components, key) for key, child in properties.items()
        }
    if schema_type == "array":
        return [example_from_schema(schema["items"], components, name)]
    if schema_type == "string":
        return example_string(name, schema)
    if schema_type == "integer":
        return 3
    if schema_type == "number":
        return 0.91
    if schema_type == "boolean":
        return False
    if isinstance(schema.get("additionalProperties"), dict):
        return {"department": "CS"}
    raise ValueError(f"Unsupported schema node for {name}: {schema!r}")


def path_for_operation(artifact: dict[str, Any], operation_id: str) -> str:
    """Resolve a served path from its operationId, so tests never hard-code URLs."""
    for path, methods in artifact["paths"].items():
        for operation in methods.values():
            if isinstance(operation, dict) and operation.get("operationId") == operation_id:
                return path
    raise RuntimeError(f"OpenAPI artifact is missing operationId {operation_id!r}")


def papers_contract(artifact: dict[str, Any]) -> dict[str, Any]:
    """Derive the finder's filters, empty shape and error contract from the artifact."""
    operation = next(
        op
        for methods in artifact["paths"].values()
        for op in methods.values()
        if isinstance(op, dict) and op.get("operationId") == PAPERS_OPERATION_ID
    )
    responses = operation["responses"]
    schemas = artifact["components"]["schemas"]
    empty = example_from_schema(schemas["PaperSearchResult"], schemas, "PaperSearchResult")
    empty["results"] = []
    # Pagination parameters carry defaults; the finder's filters do not. Web
    # sends the filters only and accepts the artifact's pagination defaults.
    parameters = operation["parameters"]
    pagination = [p["name"] for p in parameters if "default" in p["schema"]]
    return {
        "operationId": operation["operationId"],
        "filters": [p["name"] for p in parameters if p["name"] not in pagination],
        "pagination": pagination,
        "empty": empty,
        "errorStatuses": sorted(
            status
            for status, response in responses.items()
            if any(
                content.get("schema", {}).get("$ref") == "#/components/schemas/ErrorBody"
                for content in response.get("content", {}).values()
            )
        ),
        "requestIdHeader": next(iter(responses["200"]["headers"])),
    }


def artifact_payload() -> dict[str, Any]:
    """Derive routes and example payloads from the served OpenAPI artifact."""
    artifact = json.loads(OPENAPI.read_text(encoding="utf-8"))
    schemas = artifact["components"]["schemas"]
    mirrored = [
        "Query",
        "Answer",
        "Citation",
        "ImageRef",
        "ErrorBody",
        "PaperRecord",
        "PaperSearchResult",
    ]
    return {
        "source": (
            "apps/api/openapi.json (routes, payloads, filters and response declarations); "
            "ADR 0007/0009 and Lane H CONTRACTS.md (conventions)"
        ),
        "routes": {
            "query": path_for_operation(artifact, "query_api_v1_query_post"),
            "stream": path_for_operation(artifact, "stream_api_v1_query_stream_post"),
            "papers": path_for_operation(artifact, PAPERS_OPERATION_ID),
        },
        "conventions": CONVENTIONS,
        "papers": papers_contract(artifact),
        "payloads": {
            schema_name: example_from_schema(schemas[schema_name], schemas, schema_name)
            for schema_name in mirrored
        },
    }


def main() -> None:
    """Write both fixtures as stable, pretty-printed UTF-8 JSON."""
    (OUTPUT_DIR / "core-emitted.json").write_text(
        json.dumps(core_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT_DIR / "openapi-emitted.json").write_text(
        json.dumps(artifact_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
