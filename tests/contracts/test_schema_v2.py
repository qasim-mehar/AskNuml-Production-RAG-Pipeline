"""Contract assertions for the ADR 0007 schema and error additions."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import BaseModel

from tests.factories import answer, chunk, citation, document, fetch_result, image_ref, question
from uni_rag_core import (
    AuthError,
    ContentBlock,
    NotFoundError,
    RateLimitError,
    RedirectHop,
    UniRagError,
)

FIXED = datetime(2026, 1, 1, tzinfo=UTC)

FieldCase = tuple[Callable[[], BaseModel], str, Any, Any]

# (factory, field, populated value, default when absent)
CASES: list[FieldCase] = [
    (citation, "last_crawled", FIXED, None),
    (answer, "next_step", "Check the outline for updated weights.", None),
    (answer, "abstention_reason", "Weak evidence for the fee claim.", None),
    (question, "course_code", "CS-101", None),
    (question, "term", "Fall", None),
    (question, "exam_type", "Midterm", None),
    (question, "department", "Computer Science", None),
    (image_ref, "image_url", "/api/images/images/doc-1/p1.png", None),
    (chunk, "metadata", {"atomic_unit_reason": "table kept whole"}, None),
    (
        document,
        "blocks",
        [ContentBlock(kind="heading", text="Assessment", index=0)],
        [],
    ),
    (fetch_result, "headers", {"etag": '"v2"'}, {}),
    (
        fetch_result,
        "redirect_chain",
        (RedirectHop(url="https://example.edu/f", status_code=302),),
        (),
    ),
]


def _without(model: BaseModel, field: str) -> BaseModel:
    """Rebuild ``model`` without ``field`` so its declared default is exercised."""
    return type(model).model_validate(model.model_dump(exclude={field}))


@pytest.mark.parametrize(
    ("factory", "field", "value", "default"),
    CASES,
    ids=[f"{case[0].__name__}.{case[1]}" for case in CASES],
)
def test_new_field_roundtrips_populated(
    factory: Callable[[], BaseModel], field: str, value: Any, default: Any
) -> None:
    """Every new field survives JSON when populated and when absent."""
    populated = factory().model_copy(update={field: value})
    decoded = type(populated).model_validate_json(populated.model_dump_json())
    assert decoded == populated
    assert getattr(decoded, field) == value

    absent = _without(factory(), field)
    decoded_absent = type(absent).model_validate_json(absent.model_dump_json())
    assert decoded_absent == absent
    assert getattr(decoded_absent, field) == default


def test_image_url_follows_the_documented_serve_route() -> None:
    """ImageRef.image_url is the object-store proxy path for its ref_id."""
    ref = image_ref()
    assert ref.image_url == f"/api/images/{ref.ref_id}"


@pytest.mark.parametrize("error_type", [AuthError, NotFoundError, RateLimitError])
def test_new_core_errors_are_typed(error_type: type[UniRagError]) -> None:
    """The HTTP error types live in the core hierarchy and carry context."""
    error = error_type("typed failure", context={"code": "x"})
    assert isinstance(error, UniRagError)
    assert error.context["code"] == "x"

    with pytest.raises(error_type) as excinfo:
        raise error_type("raised")
    assert isinstance(excinfo.value, UniRagError)
