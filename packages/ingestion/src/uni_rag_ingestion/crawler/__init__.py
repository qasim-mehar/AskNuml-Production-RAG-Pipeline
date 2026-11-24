"""Crawler subpackage: discover and fetch source documents.

Public entry points: :class:`CrawlerConfig`, :class:`CrawlService`, the real
:class:`HttpFetcher` adapter and the pure domain helpers.
"""

from uni_rag_ingestion.crawler.adapters import HttpFetcher
from uni_rag_ingestion.crawler.domain import (
    ChangeDetector,
    ConditionalStore,
    CrawlerConfig,
    Frontier,
    RateBudget,
    canonicalize_url,
    content_hash,
    extract_links,
    extract_main_content,
    parse_robots,
)
from uni_rag_ingestion.crawler.service import CrawlReport, CrawlService

__all__ = [
    "ChangeDetector",
    "ConditionalStore",
    "CrawlReport",
    "CrawlService",
    "CrawlerConfig",
    "Frontier",
    "HttpFetcher",
    "RateBudget",
    "canonicalize_url",
    "content_hash",
    "extract_links",
    "extract_main_content",
    "parse_robots",
]
