"""Liveness and readiness probes (L3, L11)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from uni_rag_api.deps.state import health_probe
from uni_rag_api.ports import HealthProbe
from uni_rag_api.schemas import ErrorBody, LiveStatus, ReadyStatus
from uni_rag_core import PortError

router = APIRouter(tags=["health"])

Probe = Annotated[HealthProbe, Depends(health_probe)]


@router.get("/health/live", response_model=LiveStatus, summary="Liveness probe")
def live() -> LiveStatus:
    """Report that the process is up, without consulting any dependency."""
    return LiveStatus(status="ok", service="uni-rag-api")


@router.get(
    "/health/ready",
    response_model=ReadyStatus,
    summary="Readiness probe",
    responses={503: {"model": ErrorBody, "description": "Injected ports are not ready"}},
)
def ready(probe: Probe) -> ReadyStatus:
    """Report readiness after checking the injected ports' fake health."""
    if not probe.is_ready():
        raise PortError("Injected ports are not ready.", context={"probe": type(probe).__name__})
    return ReadyStatus(status="ready", service="uni-rag-api")


__all__ = ["router"]
