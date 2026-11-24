"""Pure domain logic for the crawler.

Nothing in this package performs I/O or imports an adapter (L2, L9).
"""

from uni_rag_ingestion.crawler.domain.boilerplate import MainContent, extract_main_content
from uni_rag_ingestion.crawler.domain.change_detection import (
    ChangeDecision,
    ChangeDetector,
    SoftMark,
    content_hash,
)
from uni_rag_ingestion.crawler.domain.conditionals import (
    ConditionalHeaderProvider,
    ConditionalStore,
    Validators,
)
from uni_rag_ingestion.crawler.domain.crawler_settings import CrawlerConfig
from uni_rag_ingestion.crawler.domain.frontier import Frontier, FrontierItem, canonicalize_url
from uni_rag_ingestion.crawler.domain.link_extraction import (
    ExtractedLinks,
    doc_type_for,
    extract_links,
)
from uni_rag_ingestion.crawler.domain.ratelimit import RateBudget
from uni_rag_ingestion.crawler.domain.robots import (
    RobotsDecision,
    RobotsRules,
    decide,
    parse_robots,
    robots_url,
)
from uni_rag_ingestion.crawler.domain.stats import CrawlStats, compute_stats

__all__ = [
    "ChangeDecision",
    "ChangeDetector",
    "ConditionalHeaderProvider",
    "ConditionalStore",
    "CrawlStats",
    "CrawlerConfig",
    "ExtractedLinks",
    "Frontier",
    "FrontierItem",
    "MainContent",
    "RateBudget",
    "RobotsDecision",
    "RobotsRules",
    "SoftMark",
    "Validators",
    "canonicalize_url",
    "compute_stats",
    "content_hash",
    "decide",
    "doc_type_for",
    "extract_links",
    "extract_main_content",
    "parse_robots",
    "robots_url",
]
