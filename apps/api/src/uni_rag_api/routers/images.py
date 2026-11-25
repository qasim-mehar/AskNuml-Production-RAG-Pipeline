"""Serve page images from the injected ObjectStore (ADR 0007, L3, L5, L11).

The handler is synchronous so FastAPI runs the blocking store read in a worker
thread; the event loop never waits on the object store.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from uni_rag_api.deps.auth import EnforcedApiKey
from uni_rag_api.deps.state import image_service
from uni_rag_api.openapi import declare_request_id
from uni_rag_api.ports import ImageService
from uni_rag_api.schemas import ErrorBody

router = APIRouter(
    prefix="/api",
    tags=["images"],
    responses={
        200: declare_request_id(
            {
                "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}},
                "description": "Stored page-image bytes",
            }
        ),
        404: declare_request_id(
            {"model": ErrorBody, "description": "No object for this reference id"}
        ),
        422: declare_request_id({"model": ErrorBody, "description": "Typed validation error"}),
        503: declare_request_id(
            {"model": ErrorBody, "description": "Upstream object store failure"}
        ),
    },
)
Service = Annotated[ImageService, Depends(image_service)]


@router.get(
    "/images/{ref_id:path}",
    response_class=StreamingResponse,
    summary="Stream a stored page image by reference id",
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
