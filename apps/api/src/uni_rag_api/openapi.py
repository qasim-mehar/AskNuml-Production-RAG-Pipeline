"""OpenAPI declarations shared by every router (L10, L12).

The trace middleware emits ``x-request-id`` on every response — including typed
errors and 429s — so the served artifact must document it on every operation.
"""

from typing import Any

_REQUEST_ID_HEADER: dict[str, Any] = {
    "description": "Trace id: echoes the caller's X-Trace-Id or mints a fresh id (L10).",
    "schema": {"type": "string"},
}


def declare_request_id(response: dict[str, Any]) -> dict[str, Any]:
    """Add the ``x-request-id`` response header declaration to an OpenAPI response."""
    return {
        **response,
        "headers": {**response.get("headers", {}), "x-request-id": _REQUEST_ID_HEADER},
    }


__all__ = ["declare_request_id"]
