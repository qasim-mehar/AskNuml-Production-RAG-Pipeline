"""Typed exception hierarchy (L11). No bare ``except`` anywhere in the repo."""

from typing import Any


class UniRagError(Exception):
    """Base class for every expected uni-rag error."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context or {}


class ConfigError(UniRagError):
    """Settings are missing or invalid (L8)."""


class AuthError(UniRagError):
    """A caller failed authentication or authorization (L11)."""


class NotFoundError(UniRagError):
    """A requested resource does not exist (L11)."""


class RateLimitError(UniRagError):
    """A caller exceeded its rate limit (L11)."""


class PortError(UniRagError):
    """Base for port/adapter failures."""


class FetchError(PortError):
    """An HTTP fetch failed."""


class StorageError(PortError):
    """A vector-store or object-store operation failed."""


class ValidationError(UniRagError):
    """A caller supplied an invalid argument value."""


class ParseError(UniRagError):
    """A source document could not be parsed or segmented."""


class RetrievalError(UniRagError):
    """A retrieval-stage failure."""


class AbstentionError(RetrievalError):
    """Evidence was insufficient and the system abstained (L13)."""
