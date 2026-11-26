"""Variant matrix and the L16 ablation-table row format (L16)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from uni_rag_core.errors import ValidationError

# Lane C's published chunking strategy names (ADR 0007 block vocabulary). They
# replace the old awaiting-lane-c sentinel. The combined value below is the
# integration configuration's label (not a blended corpus): integrated runs
# index the registry chunk set as-is, and the per-strategy ablation indexes it
# once under each name separately.
FIXED_WINDOW = "fixed_window"
SENTENCE_BOUNDARY = "sentence_boundary"
CHUNKING_STRATEGIES: tuple[str, ...] = (FIXED_WINDOW, SENTENCE_BOUNDARY)
# A single axis value keeps the ablation at 12 variants (3 search x 2 rerank x
# 2 freshness) while naming both strategies, matching the integration config.
INTEGRATED_CHUNKING = f"{FIXED_WINDOW}+{SENTENCE_BOUNDARY}"
# The retry_rewrite flag axis. Off is the baseline (single pass); on is Lane
# E's capped loop, measured in this milestone (L1/L16).
RETRY_REWRITE_AXIS: tuple[bool, ...] = (False, True)


class SearchMode(StrEnum):
    """Search modes offered by the ablation axis."""

    DENSE = "dense"
    LEXICAL = "lexical"
    HYBRID = "hybrid"


class NodeVariant(StrEnum):
    """The measured control-flow node axis (single pass is the baseline)."""

    SINGLE_PASS = "single-pass"
    CLARIFY = "clarify"
    MULTIHOP = "multihop"
    CHECKPOINT_FOLLOWUP = "checkpoint_followup"


# The three remaining control-flow nodes from Lane E's registry. They are not
# implemented in the shipped pipeline: this axis exists only so Lane F can run
# a node-on measurement against the single-pass baseline (L1/L16).
NODE_VARIANTS: tuple[NodeVariant, ...] = (
    NodeVariant.CLARIFY,
    NodeVariant.MULTIHOP,
    NodeVariant.CHECKPOINT_FOLLOWUP,
)


class Variant(BaseModel):
    """One ablation configuration: search, rerank, freshness, corpus and flag."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    name: str
    search_mode: SearchMode
    rerank: bool
    freshness_boost: bool
    chunking_strategy: str
    # Lane E's node flag (off by default). A retry-on variant differs from its
    # retry-off twin by this field alone; the name records the difference (L1).
    retry_rewrite: bool = False
    # Which strategy the fixture corpus was indexed under for this run. The
    # integrated baseline keeps its combined label; per-strategy runs name one
    # strategy and index the same fixture documents separately (L16).
    corpus_strategy: str = INTEGRATED_CHUNKING
    # Measurement-only node axis. The shipped pipeline never reads it; only the
    # run-only composition uses it to wrap a callable for an L16 eval run (L1/L16).
    node_variant: NodeVariant = NodeVariant.SINGLE_PASS


class NodePurposeRow(BaseModel):
    """An L16 eval row: what a graph node does and which metric measures its effect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_name: str
    purpose: str
    required_eval_row: str
    measured_effect: str


class Verdict(StrEnum):
    """L16 outcome for a measured graph node."""

    KEEP = "KEEP"
    REMOVE = "REMOVE"


def l16_verdict(gains_by_language: Mapping[str, float]) -> Verdict:
    """Return KEEP only when the measured overall recall@5 gain is strictly positive.

    L16 removes a node with no measured gain: zero and negative gains are
    REMOVE. The function is pure and reads only the ``overall`` gain, so a
    verdict can always be recomputed from the numbers printed in its own table.
    """
    overall = gains_by_language.get("overall")
    if overall is None or not isfinite(overall):
        raise ValidationError(
            "L16 verdict needs a finite overall gain",
            context={"gains": dict(gains_by_language)},
        )
    return Verdict.KEEP if overall > 0.0 else Verdict.REMOVE


def retry_rewrite_verdict(gains_by_language: Mapping[str, float]) -> Verdict:
    """F3's verdict entry point; it obeys the same pure L16 rule as every node."""
    return l16_verdict(gains_by_language)


def make_variant_name(
    search_mode: SearchMode,
    rerank: bool,
    freshness_boost: bool,
    chunking_strategy: str,
    retry_rewrite: bool = False,
    node_variant: NodeVariant = NodeVariant.SINGLE_PASS,
) -> str:
    """Return a stable, sortable name for a variant.

    Suffixes are appended only on the measured axes, so the twelve baseline
    variant names stay byte-identical and the committed gate labels do not
    drift (L1/L4).
    """
    return (
        f"{search_mode.value}-rerank-{'on' if rerank else 'off'}"
        f"-freshness-{'on' if freshness_boost else 'off'}-{chunking_strategy}"
        f"{'-retry-on' if retry_rewrite else ''}"
        f"{f'-node={node_variant.value}-on' if node_variant is not NodeVariant.SINGLE_PASS else ''}"
    )


def build_variant(
    search_mode: SearchMode,
    rerank: bool,
    freshness_boost: bool,
    chunking_strategy: str = INTEGRATED_CHUNKING,
    *,
    retry_rewrite: bool = False,
    corpus_strategy: str | None = None,
    node_variant: NodeVariant = NodeVariant.SINGLE_PASS,
) -> Variant:
    """Construct a named variant from ablation axis values."""
    indexed_under = corpus_strategy or chunking_strategy
    return Variant(
        name=make_variant_name(
            search_mode, rerank, freshness_boost, chunking_strategy, retry_rewrite, node_variant
        ),
        search_mode=search_mode,
        rerank=rerank,
        freshness_boost=freshness_boost,
        chunking_strategy=chunking_strategy,
        retry_rewrite=retry_rewrite,
        corpus_strategy=indexed_under,
        node_variant=node_variant,
    )


def variant_matrix(
    chunking_strategies: Sequence[str] = (INTEGRATED_CHUNKING,),
    *,
    retry_rewrite_axis: Sequence[bool] = (False,),
) -> tuple[Variant, ...]:
    """Cartesian product of the published ablation axes, ordered deterministically.

    ``chunking_strategies`` is the per-strategy corpus dimension: each value is
    indexed into its own corpus before querying. ``retry_rewrite_axis`` adds
    Lane E's flag as an independent axis; the default keeps the 12-variant
    baseline matrix unchanged (L1/L4).
    """
    if not chunking_strategies:
        raise ValidationError("variant_matrix needs at least one chunking strategy")
    if not retry_rewrite_axis:
        raise ValidationError("variant_matrix needs at least one retry_rewrite value")
    if any("awaiting" in strategy for strategy in chunking_strategies):
        raise ValidationError(
            "The awaiting-lane-c sentinel has been retired (Lane C published names)"
        )
    try:
        return tuple(
            build_variant(
                search_mode,
                rerank,
                freshness_boost,
                chunking_strategy,
                retry_rewrite=retry_rewrite,
                corpus_strategy=chunking_strategy,
            )
            for chunking_strategy in sorted(chunking_strategies)
            for retry_rewrite in sorted(set(retry_rewrite_axis))
            for search_mode in SearchMode
            for rerank in (False, True)
            for freshness_boost in (False, True)
        )
    except PydanticValidationError as exc:
        raise ValidationError("Invalid variant axis", context={"errors": exc.errors()}) from exc


DEFAULT_VARIANT: Variant = build_variant(SearchMode.HYBRID, True, False)


# Lane E's handoff (graph/README.md and graph/nodes.py) supplies the purpose and
# required eval row verbatim. Only the six linear stages have a measured effect;
# retry_rewrite moved from measured to removed in E3 and the three remaining
# control-flow nodes stay awaiting measurement (L16). The six linear effects are
# filled from the measured ablation by service.run.measured_l16_rows.
LANE_E_NODE_ROWS: tuple[NodePurposeRow, ...] = (
    NodePurposeRow(
        node_name="route",
        purpose="Classify language, intent and metadata filters for a query.",
        required_eval_row=(
            "Language + filter extraction exact-match on mini-golden.json; must not "
            "regress vs the linear baseline."
        ),
        measured_effect="computed from the ablation run at report generation",
    ),
    NodePurposeRow(
        node_name="filter",
        purpose="Apply extracted metadata filters to candidate chunks; never a graph branch.",
        required_eval_row=(
            "Filter precision/recall on the crafted corpus; no golden query loses its expected doc_id."
        ),
        measured_effect="computed from the ablation run at report generation",
    ),
    NodePurposeRow(
        node_name="search",
        purpose="Recall candidates with dense vectors plus in-domain lexical fusion.",
        required_eval_row=(
            "recall@k and MRR vs dense-only; lexical-only uses an injected domain-local "
            "ChunkSource for full-corpus recall."
        ),
        measured_effect="computed from the ablation run at report generation",
    ),
    NodePurposeRow(
        node_name="rerank",
        purpose="Reorder candidates through the injected Reranker port.",
        required_eval_row="nDCG@10 and MRR delta against the rerank-off ablation.",
        measured_effect="computed from the ablation run at report generation",
    ),
    NodePurposeRow(
        node_name="abstain",
        purpose="Emit an explicit, citation-free abstention with a next step when evidence is weak.",
        required_eval_row="Abstention precision on the weak-evidence fixture; zero fabricated facts.",
        measured_effect="computed from the ablation run at report generation",
    ),
    NodePurposeRow(
        node_name="answer",
        purpose="Synthesize a cited answer whose data block is delimited and labelled.",
        required_eval_row="Faithfulness and citation-resolution rate on mini-golden.json.",
        measured_effect="computed from the ablation run at report generation",
    ),
    NodePurposeRow(
        node_name="retry_rewrite",
        purpose="Rewrite a weakly retrieved query once and repeat the search (capped loop).",
        required_eval_row="recall@k gain on weak-evidence rows vs the single-pass baseline.",
        measured_effect=(
            "Removed after E3 (node deleted per L16 zero-gain verdict); "  # E3 handoff row text
            "retry_rewrite_enabled / retry_rewrite_iterations retained as dormant flags; "
            "reversal requires the parked live-transport re-run."
        ),
    ),
    NodePurposeRow(
        node_name="clarify",
        purpose="Ask the student for a missing required filter instead of guessing.",
        required_eval_row="Clarification precision after filter-extraction errors; no needless clarifications.",
        measured_effect="awaiting measurement",
    ),
    NodePurposeRow(
        node_name="multihop",
        purpose="Answer a question that must reference evidence from a second document.",
        required_eval_row="Faithfulness on a two-document multi-hop fixture.",
        measured_effect="awaiting measurement",
    ),
    NodePurposeRow(
        node_name="checkpoint_followup",
        purpose="Carry prior turns and citations into a checkpointed follow-up.",
        required_eval_row="Citation continuity and faithfulness on a follow-up fixture.",
        measured_effect="awaiting measurement",
    ),
)
