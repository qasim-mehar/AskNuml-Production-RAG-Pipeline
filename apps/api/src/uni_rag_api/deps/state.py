"""Typed accessors for app-state dependencies (L9)."""

from typing import cast

from fastapi import Request

from uni_rag_api.config import ApiSettings
from uni_rag_api.ports import AnswerService, HealthProbe


def api_settings(request: Request) -> ApiSettings:
    """Return the injected settings instance."""
    return cast("ApiSettings", request.app.state.api_settings)


def answer_service(request: Request) -> AnswerService:
    """Return the injected answer service port."""
    return cast("AnswerService", request.app.state.answer_service)


def health_probe(request: Request) -> HealthProbe:
    """Return the injected readiness probe port."""
    return cast("HealthProbe", request.app.state.health_probe)


__all__ = ["answer_service", "api_settings", "health_probe"]
