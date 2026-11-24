"""Clock port (L3) — time is injected so tests are deterministic."""

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Supplies timezone-aware UTC time."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        ...
