"""Stats spec: coverage and freshness are computed, never hand-set."""

from uni_rag_ingestion.crawler.domain import compute_stats


def test_coverage_and_freshness_are_derived_from_event_counts() -> None:
    stats = compute_stats(
        discovered=5,
        eligible=4,
        fetched=3,
        emitted=2,
        unchanged=1,
        changed=1,
        robots_blocked=1,
        redirect_blocked=0,
        rate_deferred=1,
        errors=0,
    )
    assert stats.coverage == 0.75
    assert stats.freshness == 1.0
    assert (stats.emitted, stats.unchanged, stats.changed) == (2, 1, 1)


def test_empty_run_reports_zero_ratios() -> None:
    stats = compute_stats(
        discovered=0,
        eligible=0,
        fetched=0,
        emitted=0,
        unchanged=0,
        changed=0,
        robots_blocked=0,
        redirect_blocked=0,
        rate_deferred=0,
        errors=0,
    )
    assert (stats.coverage, stats.freshness) == (0.0, 0.0)
