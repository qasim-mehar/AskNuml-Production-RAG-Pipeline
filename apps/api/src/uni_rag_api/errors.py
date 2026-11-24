"""Map typed errors to HTTP responses (L11).

Every non-2xx response uses the same typed :class:`ErrorBody`. Core error types
are mapped explicitly; an unhandled exception still produces a typed 500 with
its cause logged, never a silent bare 500.
"""

from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response
from starlette.types import ExceptionHandler

from uni_rag_api.schemas import ErrorBody
from uni_rag_core import (
    AbstentionError,
    ApiSection,
    AuthError,
    ConfigError,
    FetchError,
    NotFoundError,
    ParseError,
    PortError,
    RateLimitError,
    RetrievalError,
    StorageError,
    UniRagError,
    ValidationError,
    current_trace_id,
    get_logger,
)

_logger = get_logger("uni_rag_api.errors")

# Most specific first: isinstance matching relies on this ordering. The three
# transport errors are the folded core types (ADR 0007); no API subclasses remain.
_STATUS_BY_TYPE: tuple[tuple[type[UniRagError], int, str], ...] = (
    (AuthError, 401, "unauthorized"),
    (RateLimitError, 429, "rate_limited"),
    (NotFoundError, 404, "not_found"),
    (ValidationError, 422, "validation_error"),
    # A parse failure is an upstream/data fault, not a caller validation error.
    (ParseError, 503, "upstream_unavailable"),
    # An exception-level abstention means "no cited answer found"; the normal
    # abstention path returns a 200 Answer with abstained=True instead.
    (AbstentionError, 404, "abstained"),
    (ConfigError, 503, "configuration_error"),
    (FetchError, 503, "upstream_unavailable"),
    (StorageError, 503, "upstream_unavailable"),
    (PortError, 503, "upstream_unavailable"),
    (RetrievalError, 503, "upstream_unavailable"),
    (UniRagError, 500, "internal_error"),
)


def map_error(exc: UniRagError) -> tuple[int, str]:
    """Return ``(status_code, error_code)`` for a typed error."""
    for error_type, status, code in _STATUS_BY_TYPE:
        if isinstance(exc, error_type):
            return status, code
    return 500, "internal_error"


def _trace_id(request: Request) -> str:
    """Read the trace id from the scope, including after context teardown."""
    return str(request.scope.get("uni_rag_trace_id", "") or current_trace_id())


def _error_response(
    status: int, body: ErrorBody, *, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


async def handle_uni_rag_error(request: Request, exc: UniRagError) -> Response:
    """Render a typed core error with a structured log line."""
    status, code = map_error(exc)
    _logger.warning(
        "api.typed_error",
        method=request.method,
        path=request.url.path,
        error_code=code,
        error_type=type(exc).__name__,
        error_message=exc.message,
        context_keys=sorted(exc.context),
    )
    return _error_response(status, ErrorBody(code=code, message=exc.message, details=exc.context))


async def handle_request_validation(request: Request, exc: RequestValidationError) -> Response:
    """Render FastAPI body/query validation failures as typed 422s."""
    details = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    _logger.warning(
        "api.request_validation",
        method=request.method,
        path=request.url.path,
        error_code="validation_error",
        detail_count=len(details),
    )
    return _error_response(
        422,
        ErrorBody(
            code="validation_error",
            message="Request validation failed.",
            details={"errors": details},
        ),
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> Response:
    """Render framework HTTP exceptions with the shared error envelope."""
    status = exc.status_code
    code = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        422: "validation_error",
    }.get(status, "http_error")
    _logger.warning(
        "api.http_error",
        method=request.method,
        path=request.url.path,
        error_code=code,
        status_code=status,
    )
    return _error_response(status, ErrorBody(code=code, message=str(exc.detail)))


async def handle_unhandled(request: Request, exc: Exception) -> Response:
    """Log the typed cause and return an opaque typed 500."""
    trace_id = _trace_id(request)
    _logger.error(
        "api.unhandled_error",
        method=request.method,
        path=request.url.path,
        error_code="internal_error",
        cause=f"{type(exc).__name__}: {exc}",
        trace_id=trace_id,
    )
    settings = cast("ApiSection", request.app.state.api_settings)
    headers = (
        {settings.trace_header: trace_id} if trace_id and settings.trace_header_enabled else None
    )
    return _error_response(
        500,
        ErrorBody(code="internal_error", message="An unexpected error occurred."),
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach all error handlers to ``app``."""
    app.add_exception_handler(UniRagError, cast(ExceptionHandler, handle_uni_rag_error))
    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, handle_request_validation)
    )
    app.add_exception_handler(StarletteHTTPException, cast(ExceptionHandler, handle_http_exception))
    app.add_exception_handler(Exception, cast(ExceptionHandler, handle_unhandled))


__all__ = [
    "AuthError",
    "NotFoundError",
    "RateLimitError",
    "map_error",
    "register_error_handlers",
]
