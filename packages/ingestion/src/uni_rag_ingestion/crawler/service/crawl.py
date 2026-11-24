"""Crawl orchestration: frontier → robots → rate → fetch → hash → emit.

Only this module wires ports to domain logic (L9). All fetching and time go
through ``Fetcher`` and ``Clock``; no wall-clock or random values leak in (L4).
"""

from dataclasses import dataclass
from urllib.parse import urlsplit

from uni_rag_core import Clock, Document, Fetcher, FetchError, get_logger, trace
from uni_rag_core.logging import TraceLogger
from uni_rag_core.schemas import DocType
from uni_rag_ingestion.crawler.domain import (
    ChangeDecision,
    ChangeDetector,
    ConditionalStore,
    CrawlerConfig,
    CrawlStats,
    ExtractedLinks,
    Frontier,
    FrontierItem,
    MainContent,
    RateBudget,
    RobotsRules,
    compute_stats,
    content_hash,
    decide,
    doc_type_for,
    extract_links,
    extract_main_content,
    parse_robots,
    robots_url,
)

_LOG_NAME = "uni_rag_ingestion.crawler"


@dataclass(frozen=True)
class CrawlReport:
    """Documents emitted by a run and the counters that produced them."""

    stats: CrawlStats
    documents: tuple[Document, ...]


class CrawlService:
    """Stateful orchestrator: validator and hash state persist; rate is per run."""

    def __init__(
        self,
        config: CrawlerConfig,
        fetcher: Fetcher,
        clock: Clock,
        *,
        logger: TraceLogger | None = None,
    ) -> None:
        self._config = config
        self._fetcher = fetcher
        self._clock = clock
        self._log = logger if logger is not None else get_logger(_LOG_NAME)
        self._changes = ChangeDetector()
        self._conditionals = ConditionalStore()
        self._robots: dict[str, RobotsRules] = {}

    @property
    def conditionals(self) -> ConditionalStore:
        """The validator store; wire its ``headers_for`` into an HTTP adapter."""
        return self._conditionals

    def run(self, seeds: tuple[str, ...] | None = None) -> CrawlReport:
        """Crawl from ``seeds`` (or config seeds) and emit current documents."""
        frontier = Frontier(
            self._config.seeds if seeds is None else seeds, max_depth=self._config.max_depth
        )
        rate = RateBudget(self._config.requests_per_second)
        fetched = emitted = unchanged = changed = 0
        robots_blocked = redirect_blocked = rate_deferred = errors = 0
        documents: list[Document] = []
        deferred: list[FrontierItem] = []

        with trace():
            while True:
                progressed = False
                while (item := frontier.pop()) is not None:
                    canonical = item.canonical_url
                    host = urlsplit(canonical).hostname or canonical

                    rules = self._robots_for(canonical)
                    decision = decide(rules, canonical, self._config.user_agent)
                    if not decision.allowed:
                        robots_blocked += 1
                        self._log.warning(
                            "crawl robots blocked", url=canonical, reason=decision.reason
                        )
                        continue

                    now = self._clock.now()
                    if not rate.is_due(host, now):
                        rate_deferred += 1
                        deferred.append(item)
                        self._log.info("crawl rate deferred", url=canonical, host=host)
                        continue
                    rate.schedule(host, now)

                    try:
                        result = self._fetcher.fetch(canonical)
                    except FetchError as exc:
                        errors += 1
                        self._log.error(
                            "crawl fetch failed",
                            url=canonical,
                            reason=exc.message,
                            context=exc.context,
                        )
                        continue

                    fetched += 1
                    progressed = True
                    if result.final_url and result.final_url != canonical:
                        final_decision = decide(
                            self._robots_for(result.final_url),
                            result.final_url,
                            self._config.user_agent,
                        )
                        if not final_decision.allowed:
                            redirect_blocked += 1
                            self._log.warning(
                                "crawl redirect blocked",
                                url=canonical,
                                final_url=result.final_url,
                                reason=final_decision.reason,
                            )
                            continue

                    if result.status_code == 304:
                        unchanged += 1
                        self._log.info("crawl not modified", url=canonical, status=304)
                        continue
                    if 300 <= result.status_code < 400:
                        errors += 1
                        self._log.warning(
                            "crawl redirect not followed",
                            url=canonical,
                            final_url=result.final_url,
                            status=result.status_code,
                        )
                        continue
                    if result.status_code >= 400:
                        errors += 1
                        self._log.warning(
                            "crawl bad status", url=canonical, status=result.status_code
                        )
                        continue

                    digest = content_hash(result.body)
                    change = self._changes.evaluate(canonical, digest)
                    if change.soft_mark is not None:
                        changed += 1
                        self._log.info(
                            "crawl version bumped",
                            url=canonical,
                            version=change.version,
                            previous_version=change.soft_mark.version,
                        )

                    base_url = result.final_url or canonical
                    doc_type = doc_type_for(base_url, result.content_type)
                    main: MainContent | None = None
                    links: ExtractedLinks = ExtractedLinks((), (), ())
                    if doc_type is not DocType.PDF:
                        body_text = result.body.decode("utf-8", errors="replace")
                        main = extract_main_content(body_text)
                        links = extract_links(body_text, base_url)
                        for link in links.page_links + links.pdf_links:
                            frontier.add(link, item.depth + 1)

                    if not change.emit:
                        unchanged += 1
                        self._log.info(
                            "crawl unchanged", url=canonical, version=change.version, hash=digest
                        )
                        continue

                    document = self._build_document(
                        canonical, result.final_url, digest, change, doc_type, main, links
                    )
                    documents.append(document)
                    emitted += 1
                    self._log.info(
                        "crawl emitted",
                        url=canonical,
                        doc_id=document.doc_id,
                        version=document.version,
                        doc_type=document.doc_type.value,
                        pdf_links=len(links.pdf_links),
                        image_links=len(links.image_links),
                    )

                if deferred and progressed:
                    for pending in deferred:
                        frontier.requeue(pending)
                    deferred.clear()
                    continue
                break

            stats = compute_stats(
                discovered=len(frontier.seen),
                eligible=len(frontier.seen) - robots_blocked,
                fetched=fetched,
                emitted=emitted,
                unchanged=unchanged,
                changed=changed,
                robots_blocked=robots_blocked,
                redirect_blocked=redirect_blocked,
                rate_deferred=rate_deferred,
                errors=errors,
            )
            self._log.info(
                "crawl stats",
                discovered=stats.discovered,
                eligible=stats.eligible,
                fetched=stats.fetched,
                emitted=stats.emitted,
                unchanged=stats.unchanged,
                changed=stats.changed,
                robots_blocked=stats.robots_blocked,
                redirect_blocked=stats.redirect_blocked,
                rate_deferred=stats.rate_deferred,
                errors=stats.errors,
                coverage=stats.coverage,
                freshness=stats.freshness,
            )
        return CrawlReport(stats=stats, documents=tuple(documents))

    def _robots_for(self, canonical: str) -> RobotsRules:
        """Fetch and parse robots.txt once per host; unavailable means allow."""
        parts = urlsplit(canonical)
        host = parts.netloc
        if host in self._robots:
            return self._robots[host]
        target = robots_url(canonical)
        try:
            result = self._fetcher.fetch(target)
        except FetchError as exc:
            self._log.warning(
                "robots unavailable",
                url=target,
                reason=exc.message,
                next_step="retry robots.txt on the next run",
            )
            return RobotsRules(())
        text = result.body.decode("utf-8", errors="replace")
        if result.status_code >= 400:
            self._log.warning(
                "robots unavailable",
                url=target,
                status=result.status_code,
                next_step="retry robots.txt on the next run",
            )
            return RobotsRules(())
        rules = parse_robots(text)
        self._robots[host] = rules
        return rules

    def _build_document(
        self,
        canonical: str,
        final_url: str,
        digest: str,
        change: ChangeDecision,
        doc_type: DocType,
        main: MainContent | None,
        links: ExtractedLinks,
    ) -> Document:
        """Build a ``Document`` carrying all mandatory fields and link capture."""
        path_tail = urlsplit(canonical).path.rsplit("/", 1)[-1]
        title = (main.title if main else "") or path_tail or canonical

        metadata: dict[str, str] = {
            "canonical_url": canonical,
            "final_url": final_url,
            "page_links": ",".join(links.page_links),
            "pdf_links": ",".join(links.pdf_links),
            "image_links": ",".join(links.image_links),
        }
        if main is not None:
            metadata["main_text"] = main.text
        if change.previous_hash is not None:
            metadata["previous_content_hash"] = change.previous_hash
        if change.soft_mark is not None:
            metadata["previous_version"] = change.soft_mark.version

        return Document(
            doc_id=content_hash(canonical.encode("utf-8"))[:16],
            source_url=canonical,
            title=title,
            doc_type=doc_type,
            last_crawled=self._clock.now(),
            content_hash=digest,
            version=change.version,
            metadata=metadata,
        )
