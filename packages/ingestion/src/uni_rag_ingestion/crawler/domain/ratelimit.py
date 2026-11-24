"""Per-host token bucket driven exclusively by the Clock port (L3, L9)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from uni_rag_core.errors import ValidationError

_CAPACITY = 1.0


@dataclass
class _Bucket:
    tokens: float = _CAPACITY
    last: datetime | None = None


class RateBudget:
    """Reserve one request slot per host, spaced by ``1 / requests_per_second``.

    No sleeping happens here: the caller compares the returned time with the
    Clock value and defers the request when it is not yet due (L3).
    """

    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0 or not isfinite(requests_per_second):
            msg = "requests_per_second must be a finite positive number"
            raise ValidationError(msg, context={"requests_per_second": requests_per_second})
        self._rate = requests_per_second
        self._buckets: dict[str, _Bucket] = {}

    @property
    def requests_per_second(self) -> float:
        """The configured refill rate."""
        return self._rate

    def is_due(self, host: str, now: datetime) -> bool:
        """Report whether a slot is free at ``now`` without reserving it."""
        bucket = self._buckets.get(host)
        if bucket is None or bucket.last is None:
            return True
        elapsed = max(0.0, (now - bucket.last).total_seconds())
        return min(_CAPACITY, bucket.tokens + elapsed * self._rate) >= _CAPACITY

    def schedule(self, host: str, now: datetime) -> datetime:
        """Refill, consume one token and return the earliest allowed request time.

        When the bucket is empty the slot is reserved in the future and that
        future time is returned; no request should be sent before it.
        """
        bucket = self._buckets.setdefault(host, _Bucket())
        if bucket.last is None:
            bucket.last = now
        else:
            elapsed = max(0.0, (now - bucket.last).total_seconds())
            bucket.tokens = min(_CAPACITY, bucket.tokens + elapsed * self._rate)
            bucket.last = now

        if bucket.tokens >= _CAPACITY:
            bucket.tokens -= _CAPACITY
            return now

        scheduled = now + timedelta(seconds=(_CAPACITY - bucket.tokens) / self._rate)
        bucket.tokens = 0.0
        bucket.last = scheduled
        return scheduled
