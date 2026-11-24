"""Optional API-key stub (L3, L8).

Real identity providers are parked. When enforcement is off the dependency is
a pass-through, but the security scheme stays in OpenAPI so Lane H's contract
is stable regardless of the environment.
"""

import secrets
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from uni_rag_api.config import ApiSettings
from uni_rag_api.deps.state import api_settings
from uni_rag_api.errors import AuthenticationError

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="ApiKeyAuth")

ApiKey = Annotated[str | None, Security(_api_key_header)]
Settings = Annotated[ApiSettings, Depends(api_settings)]


def require_api_key(settings: Settings, x_api_key: ApiKey = None) -> str | None:
    """Compare ``X-API-Key`` against the typed setting in constant time."""
    if not settings.auth_enabled:
        return x_api_key
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key):
        raise AuthenticationError("A valid X-API-Key header is required.")
    return x_api_key


__all__ = ["require_api_key"]
