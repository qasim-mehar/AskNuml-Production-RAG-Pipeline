"""Register the lint-imports-safe gate marker for root-level pytest runs (L11)."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``gate`` marker so `--strict-markers` accepts it."""
    config.addinivalue_line("markers", "gate: regression gate test; select with `pytest -m gate`")
