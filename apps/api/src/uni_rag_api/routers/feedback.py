"""Local-only feedback transport contract (ADR 0009, L10, L11).

The handler validates, logs and echoes. It deliberately persists nothing:
no store port is injected or touched here.
"""

from fastapi import APIRouter, Request

from uni_rag_api.deps.auth import EnforcedApiKey
from uni_rag_api.openapi import declare_request_id
from uni_rag_api.schemas import ErrorBody, FeedbackRequest
from uni_rag_core import current_trace_id, get_logger

router = APIRouter(
    prefix="/api/v1",
    tags=["feedback"],
    responses={
        202: declare_request_id({"description": "Feedback accepted and echoed, nothing stored"}),
        401: declare_request_id({"model": ErrorBody, "description": "Missing or invalid API key"}),
        422: declare_request_id({"model": ErrorBody, "description": "Typed validation error"}),
        429: declare_request_id({"model": ErrorBody, "description": "Rate limit exceeded"}),
    },
)
_log = get_logger("uni_rag_api.routers.feedback")


@router.post(
    "/feedback",
    response_model=FeedbackRequest,
    status_code=202,
    summary="Acknowledge feedback without persisting it",
)
def feedback(body: FeedbackRequest, request: Request, _key: EnforcedApiKey) -> FeedbackRequest:
    """Validate and echo feedback, emitting one structured `feedback.received` line."""
    trace_id = str(request.scope.get("uni_rag_trace_id", "") or current_trace_id())
    _log.info(
        "feedback.received",
        answer_id=body.answer_id,
        sentiment=body.sentiment,
        reason_present=body.reason is not None,
        query_id_present=body.query_id is not None,
        trace_id=trace_id,
    )
    return body


__all__ = ["router"]
