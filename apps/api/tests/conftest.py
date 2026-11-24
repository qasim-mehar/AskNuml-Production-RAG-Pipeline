"""Fixture-first setup for the API lane (L4, L12)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from uni_rag_api.app import create_app
from uni_rag_api.config import ApiSettings
from uni_rag_core import Clock


class SteppableClock:
    """Fake Clock with an advance() method so bucket refill is deterministic."""

    def __init__(self, start: datetime | None = None) -> None:
        self.current = start if start is not None else datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        """Return the current fake time."""
        return self.current

    def advance(self, seconds: float) -> None:
        """Move fake time forward by ``seconds``."""
        self.current = self.current + timedelta(seconds=seconds)


def make_clock() -> SteppableClock:
    """Return a fresh controllable clock."""
    return SteppableClock()


@pytest.fixture
def clock() -> SteppableClock:
    """A deterministic clock shared by the app and the test."""
    return make_clock()


@pytest.fixture
def settings() -> ApiSettings:
    """High capacity keeps ordinary tests away from the rate limiter."""
    return ApiSettings(auth_enabled=False, rate_limit_capacity=1000)


@pytest.fixture
def app(settings: ApiSettings, clock: Clock) -> FastAPI:
    """The app under test, wired with fakes only."""
    return create_app(settings, clock=clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """An HTTP client bound to the fake-backed app."""
    with TestClient(app) as test_client:
        yield test_client
