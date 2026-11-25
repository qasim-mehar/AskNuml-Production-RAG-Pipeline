"""Variant matrix and the L16 ablation-table row format (L16)."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from uni_rag_core.errors import ValidationError

# Lane C's published chunking strategy names (ADR 0007 block vocabulary). They
# replace the old awaiting-lane-c sentinel; the integrated composition labels a
# run with both because the fixture corpus is chunked under both strategies.
FIXED_WINDOW = "fixed_window"
SENTENCE_BOUNDARY = "sentence_boundary"
CHUNKING_STRATEGIES: tuple[str, ...] = (FIXED_WINDOW, SENTENCE_BOUNDARY)
# A single axis value keeps the ablation at 12 variants (3 search x 2 rerank x
# 2 freshness) while naming both strategies, matching the integration config.
INTEGRATED_CHUNKING = f"{FIXED_WINDOW}+{SENTENCE_BOUNDARY}"


class SearchMode(StrEnum):
    """Search modes offered by the ablation axis."""

    DENSE = "dense"
    LEXICAL = "lexical"
    HYBRID = "hybrid"


class Variant(BaseModel):
    """One ablation configuration: search, rerank, freshness and chunking strategy."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    name: str
    search_mode: SearchMode
    rerank: bool
    freshness_boost: bool
    chunking_strategy: str


class NodePurposeRow(BaseModel):
    """An L16 eval row: what a graph node does and which metric measures its effect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_name: str
    purpose: str
    required_eval_row: str
    measured_effect: str


def make_variant_name(
    search_mode: SearchMode, rerank: bool, freshness_boost: bool, chunking_strategy: str
) -> str:
    """Return a stable, sortable name for a variant."""
    return (
        f"{search_mode.value}-rerank-{'on' if rerank else 'off'}"
        f"-freshness-{'on' if freshness_boost else 'off'}-{chunking_strategy}"
    )


def build_variant(
    search_mode: SearchMode,
    rerank: bool,
    freshness_boost: bool,
    chunking_strategy: str = INTEGRATED_CHUNKING,
) -> Variant:
    """Construct a named variant from ablation axis values."""
    return Variant(
        name=make_variant_name(search_mode, rerank, freshness_boost, chunking_strategy),
        search_mode=search_mode,
        rerank=rerank,
        freshness_boost=freshness_boost,
        chunking_strategy=chunking_strategy,
    )


def variant_matrix(
    chunking_strategies: Sequence[str] = (INTEGRATED_CHUNKING,),
) -> tuple[Variant, ...]:
    """Cartesian product of the published ablation axes, ordered deterministically."""
    if not chunking_strategies:
        raise ValidationError("variant_matrix needs at least one chunking strategy")
    if any("awaiting" in strategy for strategy in chunking_strategies):
        raise ValidationError(
            "The awaiting-lane-c sentinel has been retired (Lane C published names)"
        )
    try:
        return tuple(
            build_variant(search_mode, rerank, freshness_boost, chunking_strategy)
            for chunking_strategy in sorted(chunking_strategies)
            for search_mode in SearchMode
            for rerank in (False, True)
            for freshness_boost in (False, True)
        )
    except PydanticValidationError as exc:
        raise ValidationError("Invalid variant axis", context={"errors": exc.errors()}) from exc


DEFAULT_VARIANT: Variant = build_variant(SearchMode.HYBRID, True, False)


# Lane E's handoff (graph/README.md and graph/nodes.py) supplies the purpose and
# required eval row verbatim. Only the six linear stages have a measured effect;
# the four control-flow nodes stay awaiting measurement (L16). The six linear
# effects are filled from the measured ablation by service.run.measured_l16_rows.
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
        measured_effect="awaiting measurement",
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
