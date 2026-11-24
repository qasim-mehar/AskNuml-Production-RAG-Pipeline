# mypy: disable-error-code=import-untyped
"""Linear retrieval orchestration: route, filter, search, rerank, abstain, answer.

Only this module sequences the stages; pure logic stays in ``domain`` and all
external concerns arrive as injected core ports (L3, L9). No framework symbols
are imported here (L15).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from uni_rag_core import (
    LLM,
    Answer,
    Chunk,
    Citation,
    Clock,
    Embedder,
    ImageRef,
    Language,
    Query,
    Reranker,
    RetrievalError,
    ScoredChunk,
    Settings,
    ValidationError,
    VectorStore,
    get_logger,
)
from uni_rag_retrieval.domain.fusion import (
    ChunkSource,
    SearchMode,
    apply_freshness_boost,
    fuse,
    lexical_search,
    score_candidates,
)
from uni_rag_retrieval.domain.prompts import (
    ANSWER_SYSTEM,
    ROUTER_SYSTEM,
    abstention_text,
    build_answer_prompt,
    build_router_prompt,
    provenance_footer,
)
from uni_rag_retrieval.domain.router import (
    FilterSet,
    RouteDecision,
    matches_filters,
    parse_route_response,
    route,
)

_log = get_logger(__name__)

_SNIPPET_LENGTH = 160


def route_query(query: Query, *, router_llm: LLM | None = None) -> RouteDecision:
    """Route a query, falling back to rules when the LLM declines (L7)."""
    response = (
        router_llm.complete(build_router_prompt(query.text), system=ROUTER_SYSTEM)
        if router_llm
        else None
    )
    if response is not None and parse_route_response(response) is not None:
        return route(query.text, llm_response=response)
    return route(query.text)


def filter_chunks(chunks: Sequence[Chunk], filters: FilterSet) -> list[Chunk]:
    """Apply extracted metadata filters to a candidate pool (never a graph branch)."""
    return [chunk for chunk in chunks if matches_filters(chunk, filters)]


def hybrid_search(
    query_text: str,
    *,
    embedder: Embedder,
    vector_store: VectorStore,
    top_k: int,
    language: Language | None,
    filters: FilterSet,
    search_mode: SearchMode,
    candidate_multiplier: int,
    rrf_k: int,
    chunk_source: ChunkSource | None = None,
) -> list[Chunk]:
    """Recall candidates with dense search and fuse in in-domain lexical hits.

    An injected ``ChunkSource`` gives lexical/hybrid search the whole corpus,
    so the lexical-only ablation can recover chunks dense recall misses (L1,
    L16). The frozen ``Chunk`` schema has no ``department`` or ``course_code``
    field, so metadata filtering runs on decoded chunks rather than through
    ``VectorStore.search(filters=...)`` (CONTRACT-CHANGE note).
    """
    candidate_k = max(top_k * candidate_multiplier, top_k, 1)
    vector = embedder.embed([query_text])[0]

    # No store-side filters: the port understands doc_id/source_url/doc_type/
    # language/version, none of which correspond to the extracted filter fields.
    dense_hits = vector_store.search(vector, top_k=candidate_k)
    dense_chunks: dict[str, Chunk] = {}
    for hit in dense_hits:
        if hit.payload:
            chunk = Chunk.model_validate(hit.payload)
            dense_chunks[chunk.chunk_id] = chunk

    dense_kept = filter_chunks(list(dense_chunks.values()), filters)
    dense_ids = {chunk.chunk_id for chunk in dense_kept}
    dense_hits_kept = [hit for hit in dense_hits if hit.chunk_id in dense_ids]

    if search_mode is SearchMode.DENSE:
        ordered = [hit.chunk_id for hit in dense_hits_kept]
        selected = dense_kept
    else:
        lexical_pool = (
            list(chunk_source.iter_chunks())
            if chunk_source is not None
            else list(dense_chunks.values())
        )
        lexical_kept = filter_chunks(lexical_pool, filters)
        lexical = lexical_search(query_text, lexical_kept, top_k=candidate_k, language=language)
        if search_mode is SearchMode.LEXICAL:
            ordered = [hit.chunk_id for hit in lexical]
        else:
            ordered = fuse(dense_hits_kept, lexical, k=rrf_k)
        selected = list(dense_kept)
        known = {chunk.chunk_id for chunk in selected}
        selected.extend(chunk for chunk in lexical_kept if chunk.chunk_id not in known)

    by_id = {chunk.chunk_id: chunk for chunk in selected}
    return [by_id[chunk_id] for chunk_id in ordered if chunk_id in by_id][:top_k]


def rerank_candidates(
    query_text: str,
    candidates: Sequence[Chunk],
    *,
    reranker: Reranker,
    enabled: bool,
    language: Language | None,
) -> list[ScoredChunk]:
    """Rerank candidates via the port, or score them lexically when ablated off."""
    if enabled:
        return list(reranker.rerank(query_text, candidates))
    return score_candidates(query_text, candidates, language=language)


def maybe_boost(
    scored: Sequence[ScoredChunk],
    *,
    enabled: bool,
    now: datetime | None,
    half_life_days: float,
) -> list[ScoredChunk]:
    """Apply the freshness boost when its ablation axis is enabled."""
    if not enabled or now is None:
        return list(scored)
    return apply_freshness_boost(scored, now=now, half_life_days=half_life_days)


def build_abstention(query: Query, *, language: Language | None = None) -> Answer:
    """Return an explicit, citation-free abstention with a next step (L7, L13)."""
    answered_language = language or query.language
    return Answer(
        answer_id=f"answer-{query.query_id}",
        query_id=query.query_id,
        text=abstention_text(answered_language),
        citations=[],
        images=[],
        abstained=True,
        confidence=0.0,
        language=answered_language,
    )


def synthesize_answer(
    query: Query,
    decision: RouteDecision,
    scored: Sequence[ScoredChunk],
    *,
    llm: LLM,
    top_k: int,
) -> Answer:
    """Synthesize a cited answer, resolving page images via their ImageRefs."""
    cited = list(scored[:top_k])
    prompt = build_answer_prompt(decision.normalized_text, cited)
    completion = llm.complete(prompt, system=ANSWER_SYSTEM).strip()
    if not completion:
        msg = "LLM returned an empty completion"
        raise RetrievalError(msg, context={"query_id": query.query_id})

    citations = [
        Citation(
            chunk_id=item.chunk.chunk_id,
            doc_id=item.chunk.doc_id,
            source_url=item.chunk.source_url,
            snippet=item.chunk.text[:_SNIPPET_LENGTH],
            page=item.chunk.page,
            score=round(item.score, 6),
        )
        for item in cited
    ]
    images: list[ImageRef] = []
    seen_refs: set[str] = set()
    for item in cited:
        image_ref = item.chunk.image_ref
        if image_ref is not None and image_ref.ref_id not in seen_refs:
            seen_refs.add(image_ref.ref_id)
            images.append(image_ref)

    text = f"{completion}\n\n{provenance_footer(cited)}"
    return Answer(
        answer_id=f"answer-{query.query_id}",
        query_id=query.query_id,
        text=text,
        citations=citations,
        images=images,
        abstained=False,
        confidence=round(cited[0].score, 6) if cited else 0.0,
        language=decision.language,
    )


class RetrievalPipeline:
    """Composes the frozen ports into the shipped linear pipeline.

    ``search_mode``, ``rerank_enabled`` and ``freshness_boost_enabled`` are the
    named, constructor-injected ablation axes handed to Lane F.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        embedder: Embedder,
        vector_store: VectorStore,
        reranker: Reranker,
        llm: LLM,
        clock: Clock,
        router_llm: LLM | None = None,
        chunk_source: ChunkSource | None = None,
        search_mode: SearchMode = SearchMode.HYBRID,
        rerank_enabled: bool = True,
        freshness_boost_enabled: bool = True,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
        freshness_half_life_days: float = 365.0,
    ) -> None:
        if rrf_k <= 0:
            msg = "rrf_k must be positive"
            raise ValidationError(msg, context={"rrf_k": rrf_k})
        if candidate_multiplier <= 0:
            msg = "candidate_multiplier must be positive"
            raise ValidationError(msg, context={"candidate_multiplier": candidate_multiplier})
        if freshness_half_life_days <= 0:
            msg = "freshness_half_life_days must be positive"
            raise ValidationError(msg, context={"half_life_days": freshness_half_life_days})
        self._settings = settings
        self._embedder = embedder
        self._vector_store = vector_store
        self._reranker = reranker
        self._llm = llm
        self._clock = clock
        self._router_llm = router_llm
        self._chunk_source = chunk_source
        self._search_mode = search_mode
        self._rerank_enabled = rerank_enabled
        self._freshness_enabled = freshness_boost_enabled
        self._rrf_k = rrf_k
        self._candidate_multiplier = candidate_multiplier
        self._freshness_half_life_days = freshness_half_life_days

    def run(self, query: Query) -> Answer:
        """Run the pipeline; return citations or an explicit abstention."""
        decision = route_query(query, router_llm=self._router_llm)
        _log.debug(
            "route",
            query_id=query.query_id,
            language=decision.language.value,
            intent=decision.intent.value,
            filters=decision.filters.as_mapping(),
        )
        top_k = query.top_k if query.top_k > 0 else self._settings.default_top_k
        candidates = hybrid_search(
            decision.normalized_text,
            embedder=self._embedder,
            vector_store=self._vector_store,
            top_k=top_k,
            language=decision.language,
            filters=decision.filters,
            search_mode=self._search_mode,
            candidate_multiplier=self._candidate_multiplier,
            rrf_k=self._rrf_k,
            chunk_source=self._chunk_source,
        )
        scored = rerank_candidates(
            decision.normalized_text,
            candidates,
            reranker=self._reranker,
            enabled=self._rerank_enabled,
            language=decision.language,
        )
        scored = maybe_boost(
            scored,
            enabled=self._freshness_enabled,
            now=self._clock.now(),
            half_life_days=self._freshness_half_life_days,
        )
        top_score = scored[0].score if scored else 0.0
        if not scored or top_score < self._settings.abstention_threshold:
            _log.info("abstain", query_id=query.query_id, top_score=top_score)
            return build_abstention(query, language=decision.language)
        _log.info(
            "answer", query_id=query.query_id, top_score=top_score, citations=len(scored[:top_k])
        )
        return synthesize_answer(query, decision, scored, llm=self._llm, top_k=top_k)
