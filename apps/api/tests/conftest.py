"""Fixture-first setup for the API lane (L4, L12)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from uni_rag_api.app import create_app
from uni_rag_api.composition import (
    Backend,
    PipelinePorts,
    ephemeral_settings,
    seeded_fake_object_store,
    seeded_pipeline_ports,
)
from uni_rag_api.fixtures import REAL_BACKEND_ANSWER
from uni_rag_core import Answer, ApiSection, Clock, FakeObjectStore, Query, Settings


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
def settings() -> Settings:
    """High capacity keeps ordinary tests away from the rate limiter."""
    return ephemeral_settings(api=ApiSection(rate_limit_capacity=1000))


@pytest.fixture
def app(settings: Settings, clock: Clock) -> FastAPI:
    """The app under test, wired with fakes only."""
    return create_app(settings, clock=clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """An HTTP client bound to the fake-backed app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def image_store() -> FakeObjectStore:
    """Fake object store seeded with deterministic ADR 0007 image bytes."""
    return seeded_fake_object_store()


@pytest.fixture
def feedback_payloads() -> dict[str, Any]:
    """Valid/invalid ADR 0009 bodies, including both transliterated languages."""
    return {
        "valid": {"answer_id": "answer-en-001", "sentiment": "positive"},
        "explicit_nulls": {
            "answer_id": "answer-en-001",
            "sentiment": "positive",
            "reason": None,
            "query_id": None,
        },
        "with_reason": {
            "answer_id": "answer-ur-001",
            "sentiment": "negative",
            "reason": "جواب درست نہیں ہے",
            "query_id": "query-ur-001",
        },
        "roman_urdu": {
            "answer_id": "answer-roman-001",
            "sentiment": "positive",
            "reason": "jawab theek hai",
        },
        "invalid_sentiment": {"answer_id": "answer-en-001", "sentiment": "neutral"},
        "missing_answer_id": {"sentiment": "positive"},
        "unknown_field": {
            "answer_id": "answer-en-001",
            "sentiment": "positive",
            "stored": True,
        },
    }


@pytest.fixture
def real_backend_answer() -> Answer:
    """An answer carrying ADR 0007 provenance as a real backend would emit it."""
    return REAL_BACKEND_ANSWER


@pytest.fixture
def real_app(
    settings: Settings, clock: Clock, image_store: FakeObjectStore, real_backend_answer: Answer
) -> FastAPI:
    """Real-backend flag with a deterministic injected answer service and fake store."""

    class StubRealService:
        def answer(self, query: Query) -> Answer:
            """Return the frozen real-backend answer regardless of the query."""
            return real_backend_answer

        def tokens(self, answer: Answer) -> Iterator[str]:
            """Yield space-delimited tokens for the SSE path."""
            yield from answer.text.split(" ")

    return create_app(
        settings,
        clock=clock,
        backend=Backend.REAL,
        answer_service=StubRealService(),
        object_store=image_store,
    )


@pytest.fixture
def pipeline_ports() -> PipelinePorts:
    """Deterministic fakes injected as the real pipeline composition."""
    return seeded_pipeline_ports()


__all__ = ["SteppableClock", "make_clock"]
