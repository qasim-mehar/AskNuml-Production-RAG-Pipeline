"""Settings-driven in-memory token bucket per API key (L8).

Pure ASGI so the limiter never buffers an SSE stream. Time comes from the
injected :class:`Clock` port, so refill is deterministic under tests.
"""

import hashlib
from dataclasses import dataclass
from math import ceil

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from uni_rag_api.config import ApiSettings
from uni_rag_api.schemas import ErrorBody
from uni_rag_core import Clock
from uni_rag_core.logging import TraceLogger


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


def _header_value(scope: Scope, key: bytes) -> str | None:
    for header_key, value in scope.get("headers", []):
        if header_key.lower() == key:
            decoded: str = value.decode("latin-1")
            return decoded
    return None


def _bucket_key(api_key: str | None) -> str:
    """Never keep a raw key as state (and never log it)."""
    if api_key is None:
        return "anonymous"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


class TokenBucket:
    """Fixed-capacity bucket with linear refill driven by the injected clock."""

    def __init__(self, *, capacity: int, refill_per_second: float, clock: Clock) -> None:
        self._capacity = float(capacity)
        self._refill_rate = refill_per_second
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, key: str) -> tuple[bool, float]:
        """Consume one token, returning ``(allowed, retry_after_seconds)``."""
        now = self._clock.now().timestamp()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=self._capacity, last_refill=now)
            self._buckets[key] = bucket

        elapsed = max(0.0, now - bucket.last_refill)
        bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill_rate)
        bucket.last_refill = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, 0.0
        retry_after = ceil((1.0 - bucket.tokens) / self._refill_rate)
        return False, float(max(1, retry_after))


class RateLimitMiddleware:
    """Return a typed 429 when the caller's bucket is empty."""

    def __init__(
        self, app: ASGIApp, *, settings: ApiSettings, clock: Clock, logger: TraceLogger
    ) -> None:
        self._app = app
        self._exempt = frozenset(settings.rate_limit_exempt_paths)
        self._bucket = TokenBucket(
            capacity=settings.rate_limit_capacity,
            refill_per_second=settings.rate_limit_refill_per_second,
            clock=clock,
        )
        self._logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or path in self._exempt:
            await self._app(scope, receive, send)
            return

        api_key = _header_value(scope, b"x-api-key")
        bucket_id = _bucket_key(api_key)
        allowed, retry_after = self._bucket.allow(bucket_id)
        if not allowed:
            self._logger.warning(
                "api.rate_limited",
                path=path,
                bucket_id=bucket_id,
                retry_after_seconds=int(retry_after),
            )
            body = ErrorBody(
                code="rate_limited",
                message="Too many requests.",
                details={"retry_after_seconds": int(retry_after)},
            )
            response = JSONResponse(
                status_code=429,
                content=body.model_dump(mode="json"),
                headers={"Retry-After": str(int(retry_after))},
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)


__all__ = ["RateLimitMiddleware", "TokenBucket"]
