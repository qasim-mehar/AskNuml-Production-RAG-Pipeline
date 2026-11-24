"""Pure-ASGI trace middleware (L10).

Pure ASGI (rather than ``@app.middleware``) keeps streaming responses unbuffered
and guarantees the trace context covers every request, including 429s.
"""

import re
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from uni_rag_core.logging import TraceLogger, new_trace_id, trace

_TRACE_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}")


def _extract_trace_id(scope: Scope, header_key: bytes) -> str:
    """Accept a safe incoming trace id, otherwise mint a fresh one."""
    for key, value in scope.get("headers", []):
        if key.lower() == header_key:
            try:
                candidate: str = value.decode("ascii")
            except UnicodeDecodeError:
                break
            if _TRACE_ID_PATTERN.fullmatch(candidate):
                return candidate
            break
    return str(new_trace_id())


class TraceMiddleware:
    """Bind a trace id to context, echo it in a header and log each request."""

    def __init__(self, app: ASGIApp, *, header_name: str, logger: TraceLogger) -> None:
        self._app = app
        self._header_key = header_name.lower().encode("ascii")
        self._logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        trace_id = _extract_trace_id(scope, self._header_key)
        # The scope survives exception propagation to Starlette's outer error
        # handler, where ContextVar state has already been reset.
        scope["uni_rag_trace_id"] = trace_id
        status = 500
        started = perf_counter()

        async def send_with_trace(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                if not any(key.lower() == self._header_key for key, _ in headers):
                    headers.append((self._header_key, trace_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        with trace(trace_id):
            try:
                await self._app(scope, receive, send_with_trace)
            finally:
                duration_ms = round((perf_counter() - started) * 1000, 3)
                self._logger.info(
                    "http.request",
                    method=scope.get("method", ""),
                    path=scope.get("path", ""),
                    status_code=status,
                    duration_ms=duration_ms,
                    trace_id=trace_id,
                )


__all__ = ["TraceMiddleware"]
