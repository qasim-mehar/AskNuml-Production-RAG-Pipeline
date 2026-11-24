"""Variant matrix and the L16 ablation-table row format (L16)."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from uni_rag_core.errors import ValidationError


class SearchMode(StrEnum):
    """Search modes offered by the ablation axis."""

    DENSE = "dense"
    LEXICAL = "lexical"
    HYBRID = "hybrid"


# Lane C has not published its chunking strategy names yet. This sentinel keeps
# the axis present and honest: the table says it is waiting rather than inventing a name.
AWAITING_LANE_C = "awaiting-lane-c"


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
    chunking_strategy: str = AWAITING_LANE_C,
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
    chunking_strategies: Sequence[str] = (AWAITING_LANE_C,),
) -> tuple[Variant, ...]:
    """Cartesian product of the published ablation axes, ordered deterministically."""
    if not chunking_strategies:
        raise ValidationError("variant_matrix needs at least one chunking strategy")
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
