"""Clock implementations: the deterministic fake and the production adapter."""

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


class SystemClock:
    """Wall-clock implementation of the core ``Clock`` port (L3, ADR 0008).

    Ships next to the fake for discoverability; production paths inject it while
    tests keep injecting ``FakeClock`` so results stay deterministic (L4).
    """

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        return datetime.now(UTC)
