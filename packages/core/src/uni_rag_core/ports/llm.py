"""Large language model port (L3)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLM(Protocol):
    """Text completion behind a stable interface."""

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a completion for ``prompt``, optionally with a system message."""
        ...
