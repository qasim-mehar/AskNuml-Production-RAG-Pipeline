"""FastAPI app factory with constructor injection (L2, L3, L9).

Fakes are the default; the real pipeline is composed behind the settings flag.
Middleware is added trace-first so every response — including 429s — carries a
trace id and Lane H's ``x-request-id``.
"""

from fastapi import FastAPI

from uni_rag_api.composition import (
    Backend,
    PipelinePorts,
    build_backend,
    ephemeral_settings,
)
from uni_rag_api.errors import register_error_handlers
from uni_rag_api.middleware.rate_limit import RateLimitMiddleware
from uni_rag_api.middleware.trace import TraceMiddleware
from uni_rag_api.ports import AnswerService, HealthProbe, PaperRecordStore, PapersProvider
from uni_rag_api.routers import feedback, health, images, papers, query
from uni_rag_api.service import FakeHealthProbe, ObjectStoreImageService, as_typed_store
from uni_rag_core import Clock, FakeClock, ObjectStore, Settings
from uni_rag_core.logging import TraceLogger, get_logger


def create_app(
    settings: Settings | None = None,
    *,
    answer_service: AnswerService | None = None,
    health_probe: HealthProbe | None = None,
    clock: Clock | None = None,
    logger: TraceLogger | None = None,
    backend: Backend | None = None,
    pipeline_ports: PipelinePorts | None = None,
    object_store: ObjectStore | None = None,
    papers_provider: PapersProvider | None = None,
    paper_record_store: PaperRecordStore | None = None,
) -> FastAPI:
    """Build the API with folded core settings and injected ports (fakes by default).

    ``backend`` overrides the settings-derived flag; ``pipeline_ports``,
    ``object_store`` and ``paper_record_store`` let tests compose the real path
    deterministically with fakes (ADR 0011).
    """
    resolved_settings = settings if settings is not None else ephemeral_settings()
    resolved_clock = clock if clock is not None else FakeClock()
    resolved_logger = logger if logger is not None else get_logger("uni_rag_api")
    bundle = build_backend(
        resolved_settings,
        clock=resolved_clock,
        backend=backend,
        ports=pipeline_ports,
        object_store=object_store,
        answer_service=answer_service,
        papers_provider=papers_provider,
        paper_record_store=paper_record_store,
    )

    app = FastAPI(title="uni-rag API", version=resolved_settings.api.api_version)
    app.state.settings = resolved_settings
    app.state.api_settings = resolved_settings.api
    app.state.backend = bundle.backend
    app.state.answer_service = bundle.answer_service
    app.state.object_store = bundle.object_store
    app.state.image_service = ObjectStoreImageService(as_typed_store(bundle.object_store))
    app.state.papers_provider = bundle.papers_provider
    app.state.paper_record_store = bundle.paper_record_store
    app.state.health_probe = health_probe if health_probe is not None else FakeHealthProbe()

    register_error_handlers(app)
    # Last added is outermost: trace wraps rate limiting, which wraps the routes.
    app.add_middleware(
        RateLimitMiddleware,
        settings=resolved_settings.api,
        clock=resolved_clock,
        logger=resolved_logger,
    )
    app.add_middleware(
        TraceMiddleware,
        header_name=resolved_settings.api.trace_header,
        header_enabled=resolved_settings.api.trace_header_enabled,
        logger=resolved_logger,
    )

    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(feedback.router)
    app.include_router(images.router)
    app.include_router(papers.router)
    return app


__all__ = ["create_app"]
