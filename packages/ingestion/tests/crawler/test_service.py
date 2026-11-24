"""Crawl-service specs: politeness, idempotency, capture and exact stats."""

import logging
from collections.abc import Callable

from pytest import LogCaptureFixture

from packages.ingestion.tests.crawler.conftest import (
    BASE_URL,
    FIXED_TIME,
    DeferralLogger,
    SteppingClock,
    fetched,
)
from uni_rag_core import DocType, FakeClock, FetchResult
from uni_rag_ingestion.crawler.domain import CrawlerConfig
from uni_rag_ingestion.crawler.service import CrawlService


def config(*, max_depth: int = 2, rps: float = 1.0) -> CrawlerConfig:
    """Build a deterministic config; one slot per second keeps tests explicit."""
    return CrawlerConfig(seeds=(f"{BASE_URL}/",), max_depth=max_depth, requests_per_second=rps)


def test_robots_disallowed_url_is_never_fetched_and_logged(
    fetcher, clock, caplog: LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    report = CrawlService(config(), fetcher, clock).run()

    secret = f"{BASE_URL}/private/internal"
    assert secret not in fetcher.urls
    assert report.stats.robots_blocked == 1
    blocked = [record for record in caplog.records if record.msg == "crawl robots blocked"]
    assert blocked and blocked[0].extra_fields["reason"] == "robots disallow /private/"


def test_coverage_and_freshness_match_fixture_ground_truth(fetcher) -> None:
    report = CrawlService(config(), fetcher, SteppingClock(step=1.0)).run()
    stats = report.stats
    assert (stats.discovered, stats.eligible, stats.fetched) == (5, 4, 4)
    assert (stats.emitted, stats.unchanged, stats.changed) == (4, 0, 0)
    assert (stats.robots_blocked, stats.rate_deferred, stats.errors) == (1, 0, 0)
    assert (stats.coverage, stats.freshness) == (1.0, 1.0)
    assert len(report.documents) == 4


def test_emitted_document_carries_mandatory_metadata(fetcher) -> None:
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    document = report.documents[0]
    assert document.doc_id and document.source_url and document.content_hash
    assert document.last_crawled == FIXED_TIME
    assert document.doc_type is DocType.WEB_PAGE
    assert document.version == "1"
    assert document.metadata["canonical_url"] == f"{BASE_URL}/"


def test_requests_to_one_host_are_spaced_per_rate_limit(fetcher, clock) -> None:
    service = CrawlService(config(rps=1.0), fetcher, clock)
    first = service.run()
    assert f"{BASE_URL}/" in fetcher.urls
    assert f"{BASE_URL}/courses/cs-101" not in fetcher.urls
    assert first.stats.rate_deferred >= 1

    clock.advance(1.0)
    report = service.run(seeds=(f"{BASE_URL}/courses/cs-101",))
    assert f"{BASE_URL}/courses/cs-101" in fetcher.urls
    assert report.stats.fetched == 1


def test_unchanged_body_produces_no_new_document_or_bump(fetcher) -> None:
    service = CrawlService(config(max_depth=0), fetcher, FakeClock())
    first = service.run(seeds=(f"{BASE_URL}/",))
    assert [document.version for document in first.documents] == ["1"]

    second = service.run(seeds=(f"{BASE_URL}/",))
    assert second.documents == ()
    assert (second.stats.emitted, second.stats.unchanged) == (0, 1)
    assert second.stats.freshness == 1.0


def test_changed_body_bumps_version_and_soft_marks_old(
    fetcher, caplog: LogCaptureFixture, read_fixture: Callable[[str], str]
) -> None:
    caplog.set_level(logging.INFO)
    service = CrawlService(config(max_depth=0), fetcher, FakeClock())
    first = service.run(seeds=(f"{BASE_URL}/",))
    old_hash = first.documents[0].content_hash

    fetcher.register(
        f"{BASE_URL}/",
        fetched(f"{BASE_URL}/", read_fixture("content-v2.html").encode("utf-8")),
    )
    second = service.run(seeds=(f"{BASE_URL}/",))
    document = second.documents[0]
    assert document.version == "2"
    assert document.metadata["previous_version"] == "1"
    assert document.metadata["previous_content_hash"] == old_hash
    assert second.stats.changed == 1
    bumps = [record for record in caplog.records if record.msg == "crawl version bumped"]
    assert bumps and bumps[0].extra_fields["previous_version"] == "1"


def test_pdf_and_image_links_are_captured_on_emitted_record(fetcher) -> None:
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    document = report.documents[0]
    assert document.metadata["pdf_links"] == f"{BASE_URL}/docs/course-outline.pdf"
    assert document.metadata["image_links"] == f"{BASE_URL}/images/past-paper-1.png"
    assert document.metadata["page_links"].startswith(f"{BASE_URL}/private/internal")

    pdf_report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run(
        seeds=(f"{BASE_URL}/docs/course-outline.pdf",)
    )
    assert pdf_report.documents[0].doc_type is DocType.PDF


def test_boilerplate_is_stripped_from_emitted_document(
    fetcher, read_fixture: Callable[[str], str]
) -> None:
    fetcher.register(
        f"{BASE_URL}/",
        fetched(f"{BASE_URL}/", read_fixture("boilerplate-page.html").encode("utf-8")),
    )
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    text = report.documents[0].metadata["main_text"]
    assert "Applications close on 2026-12-01." in text
    assert "Copyright" not in text
    assert "ignore me" not in text


def test_304_empty_body_counts_as_fresh_without_emitting(fetcher) -> None:
    fetcher.register(
        f"{BASE_URL}/",
        FetchResult(
            url=f"{BASE_URL}/",
            final_url=f"{BASE_URL}/",
            status_code=304,
            content_type="text/html",
            body=b"",
        ),
    )
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    assert report.documents == ()
    assert (report.stats.fetched, report.stats.unchanged) == (1, 1)
    assert report.stats.freshness == 1.0


def test_fetch_failure_is_recorded_as_a_typed_error(empty_fetcher) -> None:
    report = CrawlService(config(max_depth=0), empty_fetcher, FakeClock()).run()
    assert report.stats.errors == 1
    assert report.documents == ()


def test_deferred_page_is_retried_in_the_same_run(timed_clock, timed_fetcher) -> None:
    report = CrawlService(config(rps=1.0), timed_fetcher, timed_clock).run()
    assert f"{BASE_URL}/courses/cs-101" in timed_fetcher.urls
    assert (report.stats.fetched, report.stats.rate_deferred) == (4, 0)
    assert report.stats.freshness == 1.0


def test_deferred_page_is_retried_after_clock_advances(fetcher, clock) -> None:
    service = CrawlService(config(rps=1.0), fetcher, clock, logger=DeferralLogger(clock))
    report = service.run()
    assert report.stats.rate_deferred >= 1
    assert f"{BASE_URL}/courses/cs-101" in fetcher.urls
    assert report.stats.fetched == 4
    assert report.stats.coverage <= 1.0


def test_bad_status_is_recorded_as_an_error(fetcher) -> None:
    fetcher.register(f"{BASE_URL}/", fetched(f"{BASE_URL}/", b"", status=400))
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    assert report.stats.errors == 1
    assert report.documents == ()


def test_unfollowed_redirect_is_an_error(fetcher) -> None:
    fetcher.register(f"{BASE_URL}/", fetched(f"{BASE_URL}/", b"", status=302))
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    assert report.stats.errors == 1
    assert report.documents == ()


def test_redirect_final_url_is_recorded_and_robots_checked(fetcher) -> None:
    redirect = FetchResult(
        url=f"{BASE_URL}/",
        final_url=f"{BASE_URL}/courses/cs-101",
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=b"<html><body>course</body></html>",
    )
    fetcher.register(f"{BASE_URL}/", redirect)
    report = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    assert report.documents[0].metadata["final_url"] == f"{BASE_URL}/courses/cs-101"

    fetcher.register(
        f"{BASE_URL}/robots.txt",
        fetched(
            f"{BASE_URL}/robots.txt",
            b"User-agent: *\nDisallow: /courses/\n",
            content_type="text/plain",
        ),
    )
    blocked = CrawlService(config(max_depth=0), fetcher, FakeClock()).run()
    assert blocked.documents == ()
    assert blocked.stats.redirect_blocked == 1
    assert blocked.stats.coverage <= 1.0
