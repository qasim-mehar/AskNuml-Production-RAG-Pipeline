"""HTTP fetch result contract."""

from pydantic import BaseModel, ConfigDict


class FetchResult(BaseModel):
    """A fetched resource. Raw bytes are kept for PDF/image parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    final_url: str
    status_code: int
    content_type: str
    body: bytes
