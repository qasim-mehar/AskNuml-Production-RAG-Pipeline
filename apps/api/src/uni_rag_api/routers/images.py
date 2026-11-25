"""Serve page images from the injected ObjectStore (ADR 0007, L3, L5, L11).

The handler is synchronous so FastAPI runs the blocking store read in a worker
thread; the event loop never waits on the object store.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from uni_rag_api.deps.auth import EnforcedApiKey
from uni_rag_api.deps.state import image_service
from uni_rag_api.ports import ImageService
from uni_rag_api.schemas import ErrorBody

router = APIRouter(prefix="/api", tags=["images"])
Service = Annotated[ImageService, Depends(image_service)]


@router.get(
    "/images/{ref_id:path}",
    response_class=StreamingResponse,
    summary="Stream a stored page image by reference id",
    responses={
        200: {
            "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}},
            "description": "Stored page-image bytes",
        },
        404: {"model": ErrorBody, "description": "No object for this reference id"},
        422: {"model": ErrorBody, "description": "Typed validation error"},
        503: {"model": ErrorBody, "description": "Upstream object store failure"},
    },
)
def get_image(ref_id: str, service: Service, _key: EnforcedApiKey) -> StreamingResponse:
    """Stream stored bytes with the content type recorded by the object store."""
    image = service.get(ref_id)
    return StreamingResponse(
        iter((image.data,)),
        media_type=image.content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


__all__ = ["router"]
