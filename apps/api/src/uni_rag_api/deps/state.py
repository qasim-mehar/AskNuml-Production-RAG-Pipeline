"""Typed accessors for app-state dependencies (L9)."""

from typing import cast

from fastapi import Request

from uni_rag_api.ports import AnswerService, HealthProbe, ImageService, PapersProvider
from uni_rag_core import ApiSection, Settings


def settings(request: Request) -> Settings:
    """Return the full folded core settings instance."""
    return cast("Settings", request.app.state.settings)


def api_settings(request: Request) -> ApiSection:
    """Return the folded API section used by HTTP knobs."""
    return cast("ApiSection", request.app.state.api_settings)


def answer_service(request: Request) -> AnswerService:
    """Return the injected answer service port."""
    return cast("AnswerService", request.app.state.answer_service)


def papers_provider(request: Request) -> PapersProvider:
    """Return the injected past-paper finder port."""
    return cast("PapersProvider", request.app.state.papers_provider)


def health_probe(request: Request) -> HealthProbe:
    """Return the injected readiness probe port."""
    return cast("HealthProbe", request.app.state.health_probe)


def image_service(request: Request) -> ImageService:
    """Return the injected image lookup port."""
    return cast("ImageService", request.app.state.image_service)


__all__ = [
    "answer_service",
    "api_settings",
    "health_probe",
    "image_service",
    "papers_provider",
    "settings",
]
