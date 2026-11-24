"""Deterministic in-memory Clock fake."""

from datetime import UTC, datetime


class FakeClock:
    """Always returns a fixed timezone-aware UTC datetime."""

    def __init__(self, fixed: datetime | None = None) -> None:
        self._fixed = fixed or datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        if self._fixed.tzinfo is None:
            msg = "fixed datetime must be timezone-aware"
            raise ValueError(msg)

    def now(self) -> datetime:
        """Return the fixed datetime."""
        return self._fixed
