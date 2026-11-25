"""Evaluation harness: drive an injected retrieval callable and score every language.

The retrieval callable is a domain-local ``Query -> Answer`` Protocol (L3). Lane
E's service can satisfy it at integration time; today a fake-backed composition
does, and the reports must always say so (L1). Trace ids are derived from the
run id and record id, never from a random generator (L4/L10).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from uni_rag_core import (
    LLM,
    Answer,
    Citation,
    Clock,
    Embedder,
    FakeEmbedder,
    FakeReranker,
    FakeVectorStore,
    Query,
    Reranker,
    VectorStore,
    get_logger,
    trace,
)
from uni_rag_core.schemas import Chunk
from uni_rag_eval.domain import metrics as metric_fns
from uni_rag_eval.domain.golden import GoldenSet
from uni_rag_eval.domain.judge import (
    FAITHFULNESS_SYSTEM_PROMPT,
    FaithfulnessJudge,
    Judgment,
    build_faithfulness_prompt,
    is_faithfulness_prompt,
    lexical_entailment,
    parse_faithfulness_prompt,
    parse_verdict,
)
from uni_rag_eval.domain.variant import SearchMode, Variant

_LOG = get_logger("uni_rag_eval.harness")
_TOKEN = re.compile(r"\w+", flags=re.UNICODE)
DEFAULT_ABSTENTION_THRESHOLD = 0.35


@runtime_checkable
class RetrievalCallable(Protocol):
    """Domain-local retrieval boundary (L3): a query in, a cited answer out."""

    def __call__(self, query: Query) -> Answer:
        """Return an ``Answer`` for ``query`` (possibly an explicit abstention)."""
        ...


@dataclass(frozen=True)
class RunContext:
    """The labels a run must carry so no number is presented without its producer."""

    run_id: str
    backend: str
    corpus: str
    variant_name: str
    chunking_strategy: str
    golden_id: str
    top_k: int
    timestamp: str
    clock: str = "unspecified"

    def fingerprint(self) -> str:
        """Return a deterministic sha256 over the labels and their order."""
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "backend": self.backend,
            "corpus": self.corpus,
            "variant_name": self.variant_name,
            "chunking_strategy": self.chunking_strategy,
            "golden_id": self.golden_id,
            "top_k": self.top_k,
            "timestamp": self.timestamp,
            "clock": self.clock,
        }
        return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PerRecordScores:
    """Scores for one golden record; the oracle tests assert these directly."""

    recall_at_k: float
    reciprocal_rank: float
    ndcg: float
    faithfulness: float


@dataclass(frozen=True)
class MetricScores:
    """Pooled scores with explicit denominators, so no aggregate hides a language."""

    recall_at_k: float
    mrr: float
    ndcg: float
    faithfulness: float
    citation_resolution: float
    abstention_precision: float
    n_records: int
    n_answerable: int
    n_answered: int
    n_abstention_decisions: int


@dataclass(frozen=True)
class QueryTrace:
    """Per-query evidence collected by the harness (L10)."""

    record_id: str
    language: str
    cited_chunk_ids: tuple[str, ...]
    answer_text: str
    abstained: bool
    trace_id: str


@dataclass(frozen=True)
class RunResult:
    """A complete scored run: labels, per-language scores, overall and traces."""

    context: RunContext
    scores_by_language: Mapping[str, MetricScores]
    overall: MetricScores
    per_record: Mapping[str, PerRecordScores]
    traces: tuple[QueryTrace, ...]


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _trace_id(run_id: str, record_id: str) -> str:
    return hashlib.sha256(f"{run_id}:{record_id}".encode()).hexdigest()[:32]


def _score_pool(
    recalls: Sequence[float],
    ranks: Sequence[float],
    ndcgs: Sequence[float],
    faiths: Sequence[float],
    decisions: Sequence[tuple[bool, bool]],
    n_records: int,
    resolutions: Sequence[float] = (),
) -> MetricScores:
    return MetricScores(
        recall_at_k=metric_fns.mean(recalls),
        mrr=metric_fns.mean(ranks),
        ndcg=metric_fns.mean(ndcgs),
        faithfulness=metric_fns.mean(faiths),
        citation_resolution=metric_fns.mean(resolutions),
        abstention_precision=metric_fns.abstention_precision(decisions),
        n_records=n_records,
        n_answerable=len(recalls),
        n_answered=len(faiths),
        n_abstention_decisions=len(decisions),
    )


def run_harness(
    golden_set: GoldenSet,
    retrieval: RetrievalCallable,
    judge: FaithfulnessJudge,
    context: RunContext,
    known_chunks: Mapping[str, Chunk] | None = None,
) -> RunResult:
    """Score every golden record, stratify by language, and log each trace.

    ``retrieval`` is the injected ``Query -> Answer`` boundary (L3); the
    integrated composition is handed to us by configuration, never imported
    from a retrieval lane. ``known_chunks`` is the corpus used for native
    citation-resolution checks via ``Citation.last_crawled`` (ADR 0007).
    """
    corpus = known_chunks or {}
    recalls: dict[str, list[float]] = defaultdict(list)
    ranks: dict[str, list[float]] = defaultdict(list)
    ndcgs: dict[str, list[float]] = defaultdict(list)
    faiths: dict[str, list[float]] = defaultdict(list)
    resolutions: dict[str, list[float]] = defaultdict(list)
    decisions: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    per_record: dict[str, PerRecordScores] = {}
    traces: list[QueryTrace] = []

    for record in golden_set.records:
        language = record.language.value
        record_trace_id = _trace_id(context.run_id, record.id)
        with trace(record_trace_id):
            query = Query(
                query_id=record.id,
                text=record.query,
                language=record.language,
                top_k=context.top_k,
                filters=dict(record.expected_filters),
            )
            answer = retrieval(query)
            retrieved = [citation.chunk_id for citation in answer.citations]
            evidence = [citation.snippet for citation in answer.citations]
            expected = list(record.expected_chunk_ids)

            record_scores = PerRecordScores(
                recall_at_k=metric_fns.recall_at_k(retrieved, expected, context.top_k),
                reciprocal_rank=metric_fns.reciprocal_rank(retrieved, expected, context.top_k),
                ndcg=metric_fns.ndcg_at_k(retrieved, expected, context.top_k),
                faithfulness=(
                    metric_fns.faithfulness([record.expected_answer_gist], evidence, judge)
                    if expected and not answer.abstained
                    else 0.0
                ),
            )
            per_record[record.id] = record_scores
            counts[language] += 1
            if expected:
                recalls[language].append(record_scores.recall_at_k)
                ranks[language].append(record_scores.reciprocal_rank)
                ndcgs[language].append(record_scores.ndcg)
            if expected and not answer.abstained:
                faiths[language].append(record_scores.faithfulness)
                resolutions[language].append(
                    metric_fns.citation_resolution(
                        [
                            (citation.chunk_id, citation.last_crawled)
                            for citation in answer.citations
                        ],
                        corpus,
                    )
                )
            decisions[language].append((answer.abstained, record.expected_abstain))
            traces.append(
                QueryTrace(
                    record_id=record.id,
                    language=language,
                    cited_chunk_ids=tuple(retrieved),
                    answer_text=answer.text,
                    abstained=answer.abstained,
                    trace_id=record_trace_id,
                )
            )
            _LOG.info(
                "eval.query.scored",
                record_id=record.id,
                language=language,
                backend=context.backend,
                recall_at_k=round(record_scores.recall_at_k, 6),
            )

    scores_by_language = {
        language: _score_pool(
            recalls[language],
            ranks[language],
            ndcgs[language],
            faiths[language],
            decisions[language],
            counts[language],
            resolutions[language],
        )
        for language in sorted(counts)
    }
    overall = _score_pool(
        [value for values in recalls.values() for value in values],
        [value for values in ranks.values() for value in values],
        [value for values in ndcgs.values() for value in values],
        [value for values in faiths.values() for value in values],
        [value for values in decisions.values() for value in values],
        sum(counts.values()),
        [value for values in resolutions.values() for value in values],
    )
    with trace(context.fingerprint()[:32]):
        _LOG.info(
            "eval.run.complete",
            run_id=context.run_id,
            backend=context.backend,
            corpus=context.corpus,
            variant=context.variant_name,
            fingerprint=context.fingerprint(),
            per_language={key: value.recall_at_k for key, value in scores_by_language.items()},
        )
    return RunResult(
        context=context,
        scores_by_language=scores_by_language,
        overall=overall,
        per_record=per_record,
        traces=tuple(traces),
    )


class FakeFaithfulnessLLM:
    """Deterministic ``LLM`` port fake: YES/NO for judge prompts, stable text otherwise."""

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a verdict for judge prompts and a prompt-derived string otherwise."""
        if is_faithfulness_prompt(prompt):
            claim, evidence = parse_faithfulness_prompt(prompt)
            return "YES" if lexical_entailment(claim, evidence) else "NO"
        return f"Fake answer: {prompt.strip()[:120]}"


class LLMJudge:
    """Judge implementation that uses the core ``LLM`` port (L3)."""

    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def judge(self, claim: str, evidence: Sequence[str]) -> Judgment:
        """Ask the LLM for a strict YES/NO verdict and parse it."""
        prompt = build_faithfulness_prompt(claim, evidence)
        completion = self._llm.complete(prompt, system=FAITHFULNESS_SYSTEM_PROMPT)
        return parse_verdict(completion)


def default_judge() -> LLMJudge:
    """Return the deterministic fake-backed judge used by default (L1/L4)."""
    return LLMJudge(FakeFaithfulnessLLM())


def _token_overlap(query: str, text: str) -> float:
    query_tokens = set(_TOKEN.findall(query.lower()))
    if not query_tokens:
        return 0.0
    text_tokens = set(_TOKEN.findall(text.lower()))
    return len(query_tokens & text_tokens) / len(query_tokens)


def _freshness(chunk: Chunk, now: datetime) -> float:
    age_days = max((now - chunk.last_crawled).days, 0)
    return max(0.0, 1.0 - age_days / 365.0)


class FakePipeline:
    """Fake-backed ``RetrievalCallable`` composed entirely from core ports (L3)."""

    def __init__(
        self,
        chunks: Sequence[Chunk],
        *,
        embedder: Embedder,
        store: VectorStore,
        reranker: Reranker,
        llm: LLM,
        clock: Clock,
        variant: Variant,
        threshold: float,
    ) -> None:
        self._chunks = tuple(chunks)
        self._embedder = embedder
        self._store = store
        self._reranker = reranker
        self._llm = llm
        self._clock = clock
        self._variant = variant
        self._threshold = threshold
        self._store.upsert(
            [(chunk, self._embedder.embed([chunk.text])[0]) for chunk in self._chunks]
        )

    def __call__(self, query: Query) -> Answer:
        """Search, optionally rerank and boost freshness, then cite or abstain."""
        vector = self._embedder.embed([query.text])[0]
        hits = self._store.search(
            vector, top_k=max(query.top_k, len(self._chunks)), filters=query.filters or None
        )
        hit_scores = {hit.chunk_id: hit.score for hit in hits}
        candidates = [chunk for chunk in self._chunks if chunk.chunk_id in hit_scores]
        now = self._clock.now()

        def score(chunk: Chunk) -> float:
            dense = (hit_scores[chunk.chunk_id] + 1.0) / 2.0
            lexical = _token_overlap(query.text, chunk.text)
            if self._variant.search_mode is SearchMode.DENSE:
                value = dense
            elif self._variant.search_mode is SearchMode.LEXICAL:
                value = lexical
            else:
                value = (dense + lexical) / 2.0
            if self._variant.freshness_boost:
                value += 0.02 * _freshness(chunk, now)
            return value

        scored = {chunk.chunk_id: score(chunk) for chunk in candidates}
        ordered = sorted(candidates, key=lambda chunk: (-scored[chunk.chunk_id], chunk.chunk_id))
        if self._variant.rerank:
            reranked = self._reranker.rerank(query.text, ordered)
            ordered = [item.chunk for item in reranked]
            scored = {item.chunk.chunk_id: item.score for item in reranked}

        top = ordered[: query.top_k]
        best = max(scored.values(), default=0.0)
        abstained = not top or best < self._threshold
        citations = (
            [
                Citation(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    source_url=chunk.source_url,
                    snippet=chunk.text[:200],
                    page=chunk.page,
                    last_crawled=chunk.last_crawled,
                    score=round(scored[chunk.chunk_id], 6),
                )
                for chunk in top
            ]
            if not abstained
            else []
        )
        answer_text = (
            ""
            if abstained
            else self._llm.complete(
                f"{query.text} | evidence: " + " ".join(citation.snippet for citation in citations)
            )
        )
        return Answer(
            answer_id=f"ans-{query.query_id}",
            query_id=query.query_id,
            text=answer_text,
            citations=citations,
            abstained=abstained,
            confidence=round(best, 6),
            language=query.language,
        )


def build_fake_pipeline(
    chunks: Sequence[Chunk],
    *,
    variant: Variant,
    clock: Clock,
    threshold: float = DEFAULT_ABSTENTION_THRESHOLD,
    embedder: Embedder | None = None,
    store: VectorStore | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
) -> FakePipeline:
    """Compose a fake-backed pipeline from ports, injecting fakes by default."""
    return FakePipeline(
        chunks,
        embedder=embedder or FakeEmbedder(),
        store=store or FakeVectorStore(),
        reranker=reranker or FakeReranker(),
        llm=llm or FakeFaithfulnessLLM(),
        clock=clock,
        variant=variant,
        threshold=threshold,
    )


def language_counts(golden_set: GoldenSet) -> Mapping[str, int]:
    """Return golden question counts per language (L7)."""
    counts: dict[str, int] = defaultdict(int)
    for record in golden_set.records:
        counts[record.language.value] += 1
    return dict(counts)
