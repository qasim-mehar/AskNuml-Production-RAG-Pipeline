"""Uvicorn entry point for the fake-backed API.

Module-level setup is intentional here: this is the process boundary, not a
library module. Tests import :func:`create_app` directly and stay side-effect
free.
"""

from uni_rag_api.app import create_app
from uni_rag_api.clock import SystemClock
from uni_rag_api.config import ApiSettings
from uni_rag_core import configure_logging

settings = ApiSettings()
configure_logging(settings.log_level)
app = create_app(settings, clock=SystemClock())
