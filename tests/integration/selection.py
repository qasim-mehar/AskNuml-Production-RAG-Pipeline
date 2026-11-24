"""Settings-driven adapter selection for the integration campaign (L8, L14).

The dataclass defaults are the CI-safe fakes. :meth:`AdapterSelection.from_settings`
is the *only* place that chooses real adapters, and it reads the already-typed
``Settings`` sections instead of the environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from uni_rag_core import Settings

FetcherKind = Literal["fake", "http"]
ParserKind = Literal["fixture", "docling"]
ChunkingKind = Literal["registry", "strategies"]
VectorStoreKind = Literal["fake", "qdrant_local", "qdrant"]
ObjectStoreKind = Literal["fake", "minio"]
MetadataKind = Literal["none", "postgres"]
ClockKind = Literal["fake", "system"]
ProviderKind = Literal["fake", "google_genai"]


@dataclass(frozen=True)
class AdapterSelection:
    """One explicit choice per port; fakes are the defaults (L4)."""

    fetcher: FetcherKind = "fake"
    parser: ParserKind = "fixture"
    chunking: ChunkingKind = "registry"
    vector_store: VectorStoreKind = "fake"
    object_store: ObjectStoreKind = "fake"
    metadata: MetadataKind = "none"
    clock: ClockKind = "fake"
    embedder: ProviderKind = "fake"
    reranker: ProviderKind = "fake"
    llm: ProviderKind = "fake"
    live_providers: bool = False

    @classmethod
    def ci_default(cls) -> AdapterSelection:
        """Return the all-fake configuration CI uses (L4)."""
        return cls()

    @classmethod
    def from_settings(cls, settings: Settings) -> AdapterSelection:
        """Select real adapters from typed settings; live stays off without a key."""
        live = settings.providers.live_enabled and settings.providers.google_api_key is not None
        return cls(
            # swap 1: fetcher -> Lane A's HttpFetcher
            fetcher="http",
            # swap 2: parsing -> Lane B's DoclingParser (fixture reader fallback)
            parser="docling",
            live_providers=live,
        )

    def backend_label(self) -> str:
        """Return a log/report label; never includes a key or secret (L1, L10)."""
        return (
            f"fetcher={self.fetcher}|parser={self.parser}|chunking={self.chunking}|"
            f"vector={self.vector_store}|objects={self.object_store}|metadata={self.metadata}|"
            f"clock={self.clock}|embedder={self.embedder}|reranker={self.reranker}|"
            f"llm={self.llm}|live={self.live_providers}"
        )
