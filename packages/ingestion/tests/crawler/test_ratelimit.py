"""Rate-budget specs: per-host token bucket paced only by injected time."""

from datetime import UTC, datetime

import pytest

from uni_rag_core import ValidationError
from uni_rag_ingestion.crawler.domain import RateBudget

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def test_same_host_slots_are_spaced_by_the_configured_rate(clock) -> None:
    budget = RateBudget(1.0)
    assert budget.is_due("example.edu", clock.now())
    assert budget.schedule("example.edu", clock.now()) == clock.now()
    assert not budget.is_due("example.edu", clock.now())

    clock.advance(0.5)
    assert not budget.is_due("example.edu", clock.now())
    clock.advance(0.5)
    assert budget.is_due("example.edu", clock.now())
    assert budget.schedule("example.edu", clock.now()) > FIXED


def test_hosts_have_independent_budgets() -> None:
    budget = RateBudget(1.0)
    assert budget.is_due("b.example", FIXED)
    assert budget.schedule("a.example", FIXED) == FIXED
    assert budget.schedule("b.example", FIXED) == FIXED
    assert not budget.is_due("a.example", FIXED)
    assert not budget.is_due("b.example", FIXED)


def test_invalid_rate_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        RateBudget(0)
