"""System clock adapter for the deployed process (L3).

The only non-fake adapter in this lane; it supplies real time to the rate
limiter at the integration edge. Tests inject a controllable fake instead.
"""

from datetime import UTC, datetime


class SystemClock:
    """Wall-clock implementation of the core ``Clock`` port."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        return datetime.now(UTC)


__all__ = ["SystemClock"]
