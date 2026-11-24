"""ETag / Last-Modified validators keyed by canonical URL (L9)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Validators:
    """Conditional-request validators for one URL."""

    etag: str | None = None
    last_modified: str | None = None

    def is_empty(self) -> bool:
        """Return ``True`` when no validator has been recorded."""
        return self.etag is None and self.last_modified is None


@runtime_checkable
class ConditionalHeaderProvider(Protocol):
    """Supplies conditional headers for a URL without exposing I/O."""

    def headers_for(self, canonical_url: str) -> dict[str, str]:
        """Return request headers such as ``If-None-Match`` for ``canonical_url``."""
        ...


class ConditionalStore:
    """In-memory validator store; the HTTP adapter consults it for headers."""

    def __init__(self) -> None:
        self._validators: dict[str, Validators] = {}

    def record(self, canonical_url: str, validators: Validators) -> None:
        """Replace the validators recorded for ``canonical_url``."""
        self._validators[canonical_url] = validators

    def record_from_headers(self, canonical_url: str, headers: Mapping[str, str]) -> None:
        """Record validators from raw response headers (case-insensitive keys).

        The frozen ``FetchResult`` carries no headers, so the orchestrator
        cannot call this today; the adapter keeps the raw headers available to
        callers that have them. See the CONTRACT-CHANGE note in the handoff.
        """
        folded = {key.lower(): value for key, value in headers.items()}
        etag = folded.get("etag")
        last_modified = folded.get("last-modified")
        if etag is None and last_modified is None:
            return
        self.record(canonical_url, Validators(etag=etag, last_modified=last_modified))

    def get(self, canonical_url: str) -> Validators | None:
        """Return the recorded validators, or ``None`` when unknown."""
        return self._validators.get(canonical_url)

    def headers_for(self, canonical_url: str) -> dict[str, str]:
        """Build ``If-None-Match`` / ``If-Modified-Since`` request headers."""
        validators = self._validators.get(canonical_url)
        if validators is None:
            return {}
        headers: dict[str, str] = {}
        if validators.etag:
            headers["If-None-Match"] = validators.etag
        if validators.last_modified:
            headers["If-Modified-Since"] = validators.last_modified
        return headers

    def forget(self, canonical_url: str) -> None:
        """Drop all validators for ``canonical_url``."""
        self._validators.pop(canonical_url, None)
