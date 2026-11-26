"""Past-paper finder route (L2, L5, L7, L8, L9, L10).

Routing and serialisation only: filter/pagination parsing stays here, record
selection stays behind the injected :class:`PapersProvider` port (L3).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from uni_rag_api.deps.auth import EnforcedApiKey
from uni_rag_api.deps.state import papers_provider
from uni_rag_api.openapi import declare_request_id
from uni_rag_api.ports import PaperFilters, PapersProvider
from uni_rag_api.schemas import ErrorBody, PaperSearchResult

_DESCRIPTION = (
    "Find segmented past-paper questions by course code, year, term, exam type and "
    "department. Every supplied filter is combined with AND; an unmatched combination "
    'returns {"results": []} with HTTP 200 — never 404 and never a null record. '
    "DATA SOURCE HONESTY: records come from the parsed-record store (ADR 0011) through "
    "the injected PapersProvider port — no fixture lookup or crawl happens at request "
    "time. Fake mode seeds that store from deterministic fixture-derived parsed "
    "records; live mode reads Lane D's persisted Postgres table. Live crawling and "
    "parsing stay parked. Each item is a PastPaperQuestion plus the `last_crawled` "
    "timestamp frozen when it was stored; source URLs, pages and image references are "
    "copied verbatim from the stored record, never invented (L1, L5)."
)

router = APIRouter(
    prefix="/api/v1",
    tags=["papers"],
    responses={
        200: declare_request_id({"description": "Matching records; empty list on no match"}),
        401: declare_request_id({"model": ErrorBody, "description": "Missing or invalid API key"}),
        422: declare_request_id({"model": ErrorBody, "description": "Typed validation error"}),
        429: declare_request_id({"model": ErrorBody, "description": "Rate limit exceeded"}),
        503: declare_request_id(
            {"model": ErrorBody, "description": "Upstream papers provider failure"}
        ),
    },
)

Provider = Annotated[PapersProvider, Depends(papers_provider)]


@router.get(
    "/papers",
    response_model=PaperSearchResult,
    summary="Find past-paper questions",
    description=_DESCRIPTION,
)
def find_papers(
    provider: Provider,
    _key: EnforcedApiKey,
    course_code: Annotated[str | None, Query(description="Course code, e.g. CS-101")] = None,
    year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    term: Annotated[str | None, Query(description="fall, spring or summer")] = None,
    exam_type: Annotated[str | None, Query(description="midterm, final or quiz")] = None,
    department: Annotated[str | None, Query(description="Department name; Urdu accepted")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaperSearchResult:
    """Return stored records matching all supplied filters (L4, L5, L7)."""
    filters = PaperFilters(
        course_code=course_code or None,
        year=year,
        term=term or None,
        exam_type=exam_type or None,
        department=department or None,
        limit=limit,
        offset=offset,
    )
    return PaperSearchResult(results=provider.find(filters))


__all__ = ["router"]
