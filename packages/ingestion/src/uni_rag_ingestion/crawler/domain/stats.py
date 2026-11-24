"""Coverage and freshness counters computed from crawl events (L1)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlStats:
    """Numbers produced by a crawl run; ratios are derived, never hand-set."""

    discovered: int
    eligible: int
    fetched: int
    emitted: int
    unchanged: int
    changed: int
    robots_blocked: int
    redirect_blocked: int
    rate_deferred: int
    errors: int
    coverage: float
    freshness: float


def compute_stats(
    *,
    discovered: int,
    eligible: int,
    fetched: int,
    emitted: int,
    unchanged: int,
    changed: int,
    robots_blocked: int,
    redirect_blocked: int,
    rate_deferred: int,
    errors: int,
) -> CrawlStats:
    """Derive coverage (fetched/eligible) and freshness (current/fetched).

    A resource is "current" when it was emitted this run or its unchanged
    digest was confirmed. No division by zero; empty runs report 0.0.
    """
    coverage = fetched / eligible if eligible else 0.0
    freshness = (emitted + unchanged) / fetched if fetched else 0.0
    return CrawlStats(
        discovered=discovered,
        eligible=eligible,
        fetched=fetched,
        emitted=emitted,
        unchanged=unchanged,
        changed=changed,
        robots_blocked=robots_blocked,
        redirect_blocked=redirect_blocked,
        rate_deferred=rate_deferred,
        errors=errors,
        coverage=coverage,
        freshness=freshness,
    )
