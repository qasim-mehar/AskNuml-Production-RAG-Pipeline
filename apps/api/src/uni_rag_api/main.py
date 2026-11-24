"""Uvicorn entry point: folded core settings and the settings-derived backend.

Module-level setup is intentional here: this is the process boundary, not a
library module. Tests import :func:`create_app` directly and stay side-effect
free.
"""

from uni_rag_api.app import create_app
from uni_rag_core import SystemClock, configure_logging, get_settings

settings = get_settings()
configure_logging(settings.api.log_level)
app = create_app(settings, clock=SystemClock())
