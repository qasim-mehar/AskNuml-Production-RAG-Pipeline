"""Node registry scaffold: names, purposes and required eval rows (L16).

Implemented entries map to plain ``service`` functions, so node logic stays in
``service`` (L9, L15). Future control-flow nodes are documented with a named
purpose and the eval row they must earn before they are added. No node is live:
``retry_rewrite``, ``clarify``, ``multihop`` and ``checkpoint_followup`` were
removed after their L16 verdicts showed zero gain.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from uni_rag_retrieval.service import pipeline as service


@dataclass(frozen=True)
class NodeSpec:
    """A node's purpose, handler and the eval row it must earn."""

    name: str
    purpose: str
    eval_row: str
    handler: Callable[..., object] | None = None

    @property
    def implemented(self) -> bool:
        """Return True when the node wraps an existing service function."""
        return self.handler is not None


NODE_SPECS: dict[str, NodeSpec] = {
    "route": NodeSpec(
        name="route",
        purpose="Classify language, intent and metadata filters for a query.",
        eval_row="Language + filter extraction exact-match on mini-golden.json; must not regress vs the linear baseline.",
        handler=service.route_query,
    ),
    "filter": NodeSpec(
        name="filter",
        purpose="Apply extracted metadata filters to candidate chunks; never a graph branch.",
        eval_row="Filter precision/recall on the crafted corpus; no golden query loses its expected doc_id.",
        handler=service.filter_chunks,
    ),
    "search": NodeSpec(
        name="search",
        purpose="Recall candidates with dense vectors plus in-domain lexical fusion.",
        eval_row="recall@k and MRR vs dense-only; lexical-only uses an injected domain-local ChunkSource for full-corpus recall.",
        handler=service.hybrid_search,
    ),
    "rerank": NodeSpec(
        name="rerank",
        purpose="Reorder candidates through the injected Reranker port.",
        eval_row="nDCG@10 and MRR delta against the rerank-off ablation.",
        handler=service.rerank_candidates,
    ),
    "abstain": NodeSpec(
        name="abstain",
        purpose="Emit an explicit, citation-free abstention with a next step when evidence is weak.",
        eval_row="Abstention precision on the weak-evidence fixture; zero fabricated facts.",
        handler=service.build_abstention,
    ),
    "answer": NodeSpec(
        name="answer",
        purpose="Synthesize a cited answer whose data block is delimited and labelled.",
        eval_row="Faithfulness and citation-resolution rate on mini-golden.json.",
        handler=service.synthesize_answer,
    ),
}

NODE_REGISTRY: dict[str, Callable[..., object]] = {
    name: spec.handler for name, spec in NODE_SPECS.items() if spec.handler is not None
}

__all__ = ["NODE_REGISTRY", "NODE_SPECS", "NodeSpec"]
