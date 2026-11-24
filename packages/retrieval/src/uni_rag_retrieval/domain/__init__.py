"""Pure domain logic for retrieval (no I/O, no framework imports)."""

from uni_rag_retrieval.domain.fusion import (
    ChunkSource,
    LexicalHit,
    SearchMode,
    apply_freshness_boost,
    freshness_multiplier,
    fuse,
    lexical_search,
    rrf,
    score_candidates,
)
from uni_rag_retrieval.domain.normalize import is_urdu_script, looks_roman_urdu, normalize, tokens
from uni_rag_retrieval.domain.router import (
    FilterSet,
    Intent,
    RouteDecision,
    detect_intent,
    detect_language,
    extract_filters,
    matches_filters,
    parse_route_response,
    route,
)

__all__ = [
    "ChunkSource",
    "FilterSet",
    "Intent",
    "LexicalHit",
    "RouteDecision",
    "SearchMode",
    "apply_freshness_boost",
    "detect_intent",
    "detect_language",
    "extract_filters",
    "freshness_multiplier",
    "fuse",
    "is_urdu_script",
    "lexical_search",
    "looks_roman_urdu",
    "matches_filters",
    "normalize",
    "parse_route_response",
    "route",
    "rrf",
    "score_candidates",
    "tokens",
]
