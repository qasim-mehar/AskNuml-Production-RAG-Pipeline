"""Optional API-key stub using the folded core settings (L3, L8, L11).

Real identity providers are parked. When enforcement is off the dependency is
a pass-through, but the security scheme stays in OpenAPI so Lane H's contract
is stable regardless of the environment.
"""

import secrets
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from uni_rag_api.deps.state import api_settings
from uni_rag_core import ApiSection, AuthError

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="ApiKeyAuth")

ApiKeyHeader = Annotated[str | None, Security(_api_key_header)]
Settings = Annotated[ApiSection, Depends(api_settings)]


def require_api_key(settings: Settings, x_api_key: ApiKeyHeader = None) -> str | None:
    """Compare ``X-API-Key`` against the typed secret in constant time."""
    if not settings.auth_enabled:
        return x_api_key
    expected = settings.api_key.get_secret_value()
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise AuthError("A valid X-API-Key header is required.")
    return x_api_key


EnforcedApiKey = Annotated[str | None, Depends(require_api_key)]

__all__ = ["EnforcedApiKey", "require_api_key"]
