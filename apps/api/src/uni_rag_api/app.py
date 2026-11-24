"""FastAPI app factory with constructor injection (L3, L9).

Fakes are the defaults; real adapters are supplied at integration. Middleware
is added trace-first so every response — including 429s — carries a trace id.
"""

from fastapi import FastAPI

from uni_rag_api.config import ApiSettings
from uni_rag_api.errors import register_error_handlers
from uni_rag_api.middleware.rate_limit import RateLimitMiddleware
from uni_rag_api.middleware.trace import TraceMiddleware
from uni_rag_api.ports import AnswerService, HealthProbe
from uni_rag_api.routers import health, query
from uni_rag_api.service import FakeAnswerService, FakeHealthProbe
from uni_rag_core import Clock, FakeClock
from uni_rag_core.logging import TraceLogger, get_logger


def create_app(
    settings: ApiSettings | None = None,
    *,
    answer_service: AnswerService | None = None,
    health_probe: HealthProbe | None = None,
    clock: Clock | None = None,
    logger: TraceLogger | None = None,
) -> FastAPI:
    """Build the API with injected settings and ports (fakes by default)."""
    resolved_settings = settings if settings is not None else ApiSettings()
    resolved_service = answer_service if answer_service is not None else FakeAnswerService()
    resolved_probe = health_probe if health_probe is not None else FakeHealthProbe()
    resolved_clock = clock if clock is not None else FakeClock()
    resolved_logger = logger if logger is not None else get_logger("uni_rag_api")

    app = FastAPI(title="uni-rag API", version=resolved_settings.api_version)
    app.state.api_settings = resolved_settings
    app.state.answer_service = resolved_service
    app.state.health_probe = resolved_probe

    register_error_handlers(app)
    # Last added is outermost: trace wraps rate limiting, which wraps the routes.
    app.add_middleware(
        RateLimitMiddleware,
        settings=resolved_settings,
        clock=resolved_clock,
        logger=resolved_logger,
    )
    app.add_middleware(
        TraceMiddleware,
        header_name=resolved_settings.trace_header,
        logger=resolved_logger,
    )

    app.include_router(health.router)
    app.include_router(query.router)
    return app


__all__ = ["create_app"]
