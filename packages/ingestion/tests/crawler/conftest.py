"""Shared deterministic helpers for Lane A crawler tests."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from uni_rag_core import FakeFetcher, FetchResult, get_logger

FIXTURES = Path(__file__).parent / "fixtures" / "html"
BASE_URL = "https://example.edu"
FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def fixture_text(name: str) -> str:
    """Read a checked-in fixture as UTF-8 text."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def fetched(
    url: str,
    body: bytes,
    *,
    content_type: str = "text/html; charset=utf-8",
    status: int = 200,
) -> FetchResult:
    """Build a ``FetchResult`` with the frozen schema fields."""
    return FetchResult(
        url=url,
        final_url=url,
        status_code=status,
        content_type=content_type,
        body=body,
    )


def fixture_responses() -> dict[str, FetchResult]:
    """The robots and page responses backing the fixture-ground-truth crawl."""
    return {
        f"{BASE_URL}/robots.txt": fetched(
            f"{BASE_URL}/robots.txt",
            fixture_text("robots.txt").encode("utf-8"),
            content_type="text/plain",
        ),
        f"{BASE_URL}/": fetched(f"{BASE_URL}/", fixture_text("pdf-links-page.html").encode()),
        f"{BASE_URL}/courses/cs-101": fetched(
            f"{BASE_URL}/courses/cs-101", fixture_text("content-v1.html").encode()
        ),
        f"{BASE_URL}/docs/course-outline.pdf": fetched(
            f"{BASE_URL}/docs/course-outline.pdf",
            b"%PDF-1.4\nfixture course outline\n%%EOF\n",
            content_type="application/pdf",
        ),
        f"{BASE_URL}/footer-link": fetched(
            f"{BASE_URL}/footer-link", b"<html><body><h1>Footer</h1></body></html>"
        ),
        f"{BASE_URL}/private/internal": fetched(
            f"{BASE_URL}/private/internal", b"<html><body>secret</body></html>"
        ),
    }


class AdvancingClock:
    """Clock double whose time moves only when a test advances it (L4)."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or FIXED_TIME

    def now(self) -> datetime:
        """Return the current test time."""
        return self._now

    def advance(self, seconds: float) -> None:
        """Move time forward by ``seconds``."""
        self._now += timedelta(seconds=seconds)


class SteppingClock:
    """Advances by a fixed step on each ``now()`` call (deterministic)."""

    def __init__(self, step: float = 1.0, start: datetime | None = None) -> None:
        self._step = timedelta(seconds=step)
        self._now = start or FIXED_TIME

    def now(self) -> datetime:
        """Return the current time, then step forward."""
        current = self._now
        self._now += self._step
        return current


class AdvanceOnFetchClock:
    """Advances one interval when a fetch completes; time passes with I/O (L4)."""

    def __init__(self, step: float = 1.0, start: datetime | None = None) -> None:
        self._step = timedelta(seconds=step)
        self._now = start or FIXED_TIME

    def now(self) -> datetime:
        """Return the current test time."""
        return self._now

    def advance(self) -> None:
        """Move time forward by one fetch interval."""
        self._now += self._step


class RecordingFetcher:
    """Wraps ``FakeFetcher`` and records every URL the service asks for."""

    def __init__(
        self,
        responses: Mapping[str, FetchResult],
        *,
        on_fetch: Callable[[], None] | None = None,
    ) -> None:
        self._inner = FakeFetcher(responses)
        self._on_fetch = on_fetch
        self.urls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        """Delegate to the fake, record the request and notify the clock."""
        self.urls.append(url)
        result = self._inner.fetch(url)
        if self._on_fetch is not None:
            self._on_fetch()
        return result

    def register(self, url: str, response: FetchResult) -> None:
        """Replace a registered response for change-detection tests."""
        self._inner.register(url, response)


@pytest.fixture
def clock() -> AdvancingClock:
    """A deterministic, advanceable Clock."""
    return AdvancingClock()


class DeferralLogger:
    """Advances the clock when a deferral is logged, so requeue paths are testable."""

    def __init__(self, clock: AdvancingClock) -> None:
        self._clock = clock
        self._inner = get_logger("uni_rag_ingestion.crawler.tests")

    def debug(self, message: str, **extra: object) -> None:
        """Forward a debug log."""
        self._inner.debug(message, **extra)

    def info(self, message: str, **extra: object) -> None:
        """Advance time on a deferral, then forward an info log."""
        if message == "crawl rate deferred":
            self._clock.advance(1.0)
        self._inner.info(message, **extra)

    def warning(self, message: str, **extra: object) -> None:
        """Forward a warning log."""
        self._inner.warning(message, **extra)

    def error(self, message: str, **extra: object) -> None:
        """Forward an error log."""
        self._inner.error(message, **extra)


@pytest.fixture
def read_fixture() -> Callable[[str], str]:
    """Expose the fixture reader to tests without importing conftest directly."""
    return fixture_text


@pytest.fixture
def timed_clock() -> AdvanceOnFetchClock:
    """A clock advanced by completed fetches."""
    return AdvanceOnFetchClock()


@pytest.fixture
def timed_fetcher(timed_clock: AdvanceOnFetchClock) -> RecordingFetcher:
    """A fetcher whose completions advance ``timed_clock``."""
    return RecordingFetcher(fixture_responses(), on_fetch=timed_clock.advance)


@pytest.fixture
def empty_fetcher() -> RecordingFetcher:
    """A fetcher with only robots.txt, so the seed fetch raises ``FetchError``."""
    return RecordingFetcher(
        {
            f"{BASE_URL}/robots.txt": fetched(
                f"{BASE_URL}/robots.txt", b"User-agent: *\n", content_type="text/plain"
            )
        }
    )


@pytest.fixture
def fetcher() -> RecordingFetcher:
    """A fake fetcher seeded with the robots and fixture pages."""
    return RecordingFetcher(fixture_responses())


__all__ = [
    "BASE_URL",
    "FIXED_TIME",
    "AdvanceOnFetchClock",
    "AdvancingClock",
    "DeferralLogger",
    "RecordingFetcher",
    "SteppingClock",
    "fetched",
    "fetcher",
    "clock",
    "fixture_text",
]
