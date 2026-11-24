"""HTTP fetch result contract."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class RedirectHop(BaseModel):
    """One hop of a fetch redirect chain, with the status that produced it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    status_code: int


class FetchResult(BaseModel):
    """A fetched resource. Raw bytes are kept for PDF/image parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    final_url: str
    status_code: int
    content_type: str
    body: bytes
    headers: Mapping[str, str] = Field(default_factory=dict)
    redirect_chain: tuple[RedirectHop, ...] = ()
