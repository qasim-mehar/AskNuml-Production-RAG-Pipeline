"""Query and SSE streaming routes (L2, L5, L6, L7, L9).

Only routing and serialisation live here; answer orchestration stays inside the
injected service port.
"""

import json
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from uni_rag_api.deps.auth import EnforcedApiKey
from uni_rag_api.deps.state import answer_service, api_settings
from uni_rag_api.openapi import declare_request_id
from uni_rag_api.ports import AnswerService
from uni_rag_api.schemas import Answer, CitationsEvent, ErrorBody, TokenEvent
from uni_rag_core import ApiSection, Query, ValidationError

router = APIRouter(
    prefix="/api/v1",
    tags=["query"],
    responses={200: declare_request_id({"description": "Successful Response"})},
)

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: declare_request_id({"model": ErrorBody, "description": "Missing or invalid API key"}),
    422: declare_request_id({"model": ErrorBody, "description": "Typed validation error"}),
    429: declare_request_id({"model": ErrorBody, "description": "Rate limit exceeded"}),
    503: declare_request_id({"model": ErrorBody, "description": "Upstream port failure"}),
}

_STREAM_DESCRIPTION = (
    "Server-Sent Events (`text/event-stream`) with two API-local envelopes (ADR 0009). "
    '`event: token` carries `TokenEvent` = {"token": "<string>"}, one frame per '
    "ordered token; the tokens rejoin to the answer text exactly. The final frame is "
    '`event: citations`, carrying `CitationsEvent` = {"answer": <Answer>} with the '
    "full cited answer and its L5/L6 provenance. No `citation`, `image`, `answer` or "
    "`error` event is emitted; non-2xx failures are HTTP `ErrorBody` responses, never "
    "an SSE frame. SSE envelopes stay in `uni_rag_api.schemas` (no core port)."
)

Settings = Annotated[ApiSection, Depends(api_settings)]
Service = Annotated[AnswerService, Depends(answer_service)]
ApiKey = EnforcedApiKey


def _check_top_k(query: Query, settings: ApiSection) -> None:
    """Enforce the typed top_k ceiling before the service is called."""
    if query.top_k > settings.max_top_k:
        raise ValidationError(
            f"top_k must not exceed {settings.max_top_k}.",
            context={"top_k": query.top_k, "max_top_k": settings.max_top_k},
        )


def _sse(event: str, payload: BaseModel) -> str:
    """Frame one SSE event with UTF-8 JSON (no ASCII escaping)."""
    data = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


@router.post(
    "/query",
    response_model=Answer,
    summary="Return a cited answer",
    responses=_ERROR_RESPONSES,
)
def query(body: Query, settings: Settings, service: Service, _key: ApiKey) -> Answer:
    """Return the exact cited Answer for a query (or an explicit abstention)."""
    _check_top_k(body, settings)
    return service.answer(body)


@router.post(
    "/query/stream",
    response_class=StreamingResponse,
    summary="Stream answer tokens",
    description=_STREAM_DESCRIPTION,
    responses=_ERROR_RESPONSES,
)
def stream(body: Query, settings: Settings, service: Service, _key: ApiKey) -> StreamingResponse:
    """Stream ordered tokens, ending with a citations event carrying the Answer."""
    _check_top_k(body, settings)
    answer = service.answer(body)

    def events() -> Iterator[str]:
        for token in service.tokens(answer):
            yield _sse("token", TokenEvent(token=token))
        yield _sse("citations", CitationsEvent(answer=answer))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["router"]
