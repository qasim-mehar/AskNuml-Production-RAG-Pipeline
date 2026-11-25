"""Past-paper finder filters, provenance and honest empty state (L4, L5, L7, L8)."""

from typing import Any

import pytest
from conftest import SteppableClock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from uni_rag_api.app import create_app
from uni_rag_api.composition import ephemeral_settings
from uni_rag_api.fixtures import IMAGE_BYTES, LAST_CRAWLED, PAPER_RECORDS

EN_ID = "question-paper-2024-1"
UR_ID = "question-paper-2024-2"
SPRING_ID = "question-paper-2023-7"
URDU_COURSE_ID = "question-paper-2024-urdu-3"
ALL_IDS = [EN_ID, UR_ID, SPRING_ID, URDU_COURSE_ID]


def _ids(client: TestClient, params: dict[str, Any] | None = None) -> list[str]:
    """Return question ids from the finder response in order."""
    response = client.get("/api/v1/papers", params=params)
    assert response.status_code == 200
    return [item["question_id"] for item in response.json()["results"]]


def test_unfiltered_finder_returns_every_fixture_record_in_order(client: TestClient) -> None:
    """No filters means no constraints; fixture order is deterministic (L4)."""
    assert _ids(client) == ALL_IDS


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"course_code": "CS-101"}, [EN_ID, UR_ID, SPRING_ID]),
        ({"year": 2024}, [EN_ID, UR_ID, URDU_COURSE_ID]),
        ({"term": "fall"}, [EN_ID, UR_ID, URDU_COURSE_ID]),
        ({"exam_type": "final"}, [EN_ID, UR_ID, URDU_COURSE_ID]),
        ({"department": "Computer Science"}, [EN_ID, SPRING_ID]),
        ({"course_code": "اردو-101"}, [URDU_COURSE_ID]),
    ],
)
def test_each_filter_returns_exactly_the_fixture_matches(
    client: TestClient, params: dict[str, Any], expected: list[str]
) -> None:
    """Each filter constrains results independently of the others."""
    assert _ids(client, params) == expected


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (
            {
                "course_code": "CS-101",
                "year": 2024,
                "term": "fall",
                "exam_type": "final",
                "department": "کمپیوٹر سائنس",
            },
            [UR_ID],
        ),
        (
            {
                "course_code": "CS-101",
                "year": 2024,
                "term": "fall",
                "exam_type": "final",
                "department": "Computer Science",
            },
            [EN_ID],
        ),
        ({"course_code": "CS-101", "year": 2023, "term": "fall"}, []),
        ({"department": "کمپیوٹر سائنس", "exam_type": "midterm"}, []),
    ],
)
def test_filters_combine_with_and_and_expose_an_explicit_empty_state(
    client: TestClient, params: dict[str, Any], expected: list[str]
) -> None:
    """AND semantics hold; an unmatched combination is a 200 empty list, never 404/null."""
    response = client.get("/api/v1/papers", params=params)

    assert response.status_code == 200
    assert response.json() == {"results": [r for r in _expected_records(expected)]}


def _expected_records(ids: list[str]) -> list[dict[str, Any]]:
    """Dump the fixture records selected by id for the exact-body assertion."""
    return [record.model_dump(mode="json") for record in PAPER_RECORDS if record.question_id in ids]


def test_urdu_filter_values_round_trip_byte_faithfully(client: TestClient) -> None:
    """Urdu department/course values filter and return without ASCII escaping (L7)."""
    response = client.get("/api/v1/papers", params={"department": "کمپیوٹر سائنس"})

    assert response.status_code == 200
    assert "\\u" not in response.text
    assert "کمپیوٹر سائنس" in response.text
    results = response.json()["results"]
    assert [item["question_id"] for item in results] == [UR_ID, URDU_COURSE_ID]
    assert all(item["department"] == "کمپیوٹر سائنس" for item in results)

    urdu_course = client.get("/api/v1/papers", params={"course_code": "اردو-101"}).json()
    assert [item["question_id"] for item in urdu_course["results"]] == [URDU_COURSE_ID]
    assert urdu_course["results"][0]["text"] == "امتحان میں ایک سوال حل کریں۔"


def test_every_record_carries_fixture_provenance_verbatim(client: TestClient) -> None:
    """source_url, last_crawled, page and image refs come from fixtures only (L5)."""
    results = client.get("/api/v1/papers").json()["results"]

    assert results == [record.model_dump(mode="json") for record in PAPER_RECORDS]
    assert [item["source_url"] for item in results] == [
        "https://example.edu/papers/2024.pdf",
        "https://example.edu/urdu/courses/cs101",
        "https://example.edu/courses/cs101/assessment",
        "https://example.edu/urdu/courses/cs101",
    ]
    assert [item["page"] for item in results] == [1, 3, 3, 4]
    for item, record in zip(results, PAPER_RECORDS, strict=True):
        assert item["source_url"] == record.source_url
        assert item["page"] == record.page
        assert item["last_crawled"] == LAST_CRAWLED.isoformat().replace("+00:00", "Z")
        assert item["image_ref"] == (
            record.image_ref.model_dump(mode="json") if record.image_ref is not None else None
        )


def test_image_bearing_record_points_at_a_really_seeded_object(client: TestClient) -> None:
    """The advertised image reference is served by the image route, not invented (L5)."""
    response = client.get("/api/v1/papers", params={"course_code": "CS-101", "year": 2024})
    image = next(item["image_ref"] for item in response.json()["results"] if item["image_ref"])

    assert image["ref_id"] == "images/papers/2024-p1.png"
    assert image["ref_id"] in IMAGE_BYTES
    assert image["image_url"] == "/api/images/images/papers/2024-p1.png"
    assert client.get(image["image_url"]).status_code == 200


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"limit": 2}, ALL_IDS[:2]),
        ({"offset": 2, "limit": 1}, ALL_IDS[2:3]),
        ({"offset": 99, "limit": 2}, []),
    ],
)
def test_pagination_limits_are_typed_route_parameters(
    client: TestClient, params: dict[str, Any], expected: list[str]
) -> None:
    """Pagination is bounded at the route; settings are never read (L8)."""
    assert _ids(client, params) == expected


def test_blank_filter_values_mean_no_constraint(client: TestClient) -> None:
    """Web sends non-empty keys only; an explicit blank is still not a filter (L7)."""
    assert _ids(client, {"course_code": "", "department": ""}) == ALL_IDS


@pytest.mark.parametrize(
    "params",
    [
        {"year": "not-a-year"},
        {"year": 999},
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
    ],
)
def test_invalid_filters_and_pagination_produce_typed_422(
    client: TestClient, params: dict[str, Any]
) -> None:
    """Bad query parameters use the shared typed error envelope (L11)."""
    response = client.get("/api/v1/papers", params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.headers["x-request-id"]


def test_papers_route_honours_the_trace_middleware(client: TestClient) -> None:
    """Papers requests carry the same trace id as queries (L10)."""
    response = client.get("/api/v1/papers", headers={"X-Trace-Id": "papers-trace-1"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "papers-trace-1"
    assert response.headers["X-Trace-Id"] == "papers-trace-1"


def test_finder_uses_the_injected_provider_port(clock: SteppableClock) -> None:
    """No provider is constructed inside the router; tests can inject one (L3, L14)."""
    injected = PAPER_RECORDS[:1]

    class StubPapersProvider:
        def find(self, filters: Any) -> list[Any]:
            """Return the single injected record."""
            return list(injected)

    app: FastAPI = create_app(
        ephemeral_settings(), clock=clock, papers_provider=StubPapersProvider()
    )
    with TestClient(app) as client:
        results = client.get("/api/v1/papers").json()["results"]

    assert [item["question_id"] for item in results] == [EN_ID]
