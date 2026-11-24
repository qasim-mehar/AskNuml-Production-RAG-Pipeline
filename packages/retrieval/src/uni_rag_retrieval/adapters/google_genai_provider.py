"""google-genai adapter for ``LLM``, ``Embedder`` and page images (L3, L15, L17).

The SDK is imported lazily inside ``live_*`` factories, which only the
application calls after live mode is opted in (ADR 0002). Default transports are
deterministic hash functions, so the shared contract suite passes offline and
no framework type crosses a port. Page images use the existing ``ImageRef``
schema and ``ObjectStore`` port; no core port is added.
"""

from __future__ import annotations

import hashlib
import importlib
import math
import sys
from collections.abc import Callable, Sequence
from typing import Any

from uni_rag_core import ObjectStore, PortError, ValidationError
from uni_rag_core.schemas import ImageRef

CompletionTransport = Callable[[str, str | None], str]
EmbeddingTransport = Callable[[Sequence[str], int], list[list[float]]]
ImageTransport = Callable[[bytes, str], list[float]]


class GoogleGenaiSDKError(Exception):
    """Offline stand-in for a google-genai SDK failure (L11).

    The SDK is an optional extra and is never installed in CI, so transports
    exercised by tests raise this typed marker instead of a real SDK error.
    """


def _sdk_error_types() -> tuple[type[BaseException], ...]:
    """Return the real SDK exception types when loaded, plus the offline marker.

    Resolved from ``sys.modules`` only, so importing this adapter never pulls in
    the optional SDK (L15). Unexpected Python errors are deliberately not caught:
    they must propagate instead of being swallowed (L11).
    """
    errors = sys.modules.get("google.genai.errors")
    api_error = getattr(errors, "APIError", None) if errors is not None else None
    if isinstance(api_error, type) and issubclass(api_error, BaseException):
        return (api_error, GoogleGenaiSDKError)
    return (GoogleGenaiSDKError,)


def _hash_vector(payload: bytes, dimension: int) -> list[float]:
    digest = hashlib.sha256(payload).digest()
    return [round(digest[index % len(digest)] / 127.5 - 1.0, 6) for index in range(dimension)]


def _conform_vectors(
    vectors: list[list[float]], *, dimension: int, count: int, provider: str
) -> list[list[float]]:
    """Enforce the frozen Embedder contract: fixed width, finite values in [-1, 1]."""
    if len(vectors) != count or any(len(vector) != dimension for vector in vectors):
        msg = f"{provider} returned vectors of the wrong shape"
        raise PortError(msg, context={"dimension": dimension, "received": len(vectors)})
    conformed: list[list[float]] = []
    for vector in vectors:
        row: list[float] = []
        for value in vector:
            numeric = float(value)
            if not math.isfinite(numeric):
                msg = f"{provider} returned a non-finite embedding"
                raise PortError(msg)
            row.append(max(-1.0, min(1.0, numeric)))
        conformed.append(row)
    return conformed


def _offline_completion(prompt: str, system: str | None) -> str:
    prefix = f"{system.strip()} " if system and system.strip() else ""
    return f"{prefix}google-genai[offline]: {prompt.strip()[:120]}"


def _offline_embedding(texts: Sequence[str], dimension: int) -> list[list[float]]:
    return [_hash_vector(f"google-genai:{text}".encode(), dimension) for text in texts]


def _offline_image_transport(dimension: int) -> ImageTransport:
    def embed(data: bytes, mime_type: str) -> list[float]:
        return _hash_vector(f"google-genai-image:{mime_type}:".encode() + data, dimension)

    return embed


def _load_genai() -> Any:
    """Import the SDK only when live mode is explicitly constructed."""
    try:
        return importlib.import_module("google.genai")
    except ImportError as exc:
        msg = "google-genai is not installed; enable the 'google' extra for live mode"
        raise PortError(msg, context={"extra": "google"}) from exc


def live_completion_transport(*, model: str, api_key: str | None = None) -> CompletionTransport:
    """Build a live completion transport; never called from tests or CI."""
    genai = _load_genai()
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def transport(prompt: str, system: str | None) -> str:
        config = genai.types.GenerateContentConfig(system_instruction=system) if system else None
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        return str(response.text or "")

    return transport


def live_embedding_transport(*, model: str, api_key: str | None = None) -> EmbeddingTransport:
    """Build a live embedding transport; never called from tests or CI."""
    genai = _load_genai()
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def transport(texts: Sequence[str], dimension: int) -> list[list[float]]:
        del dimension  # The remote model fixes its own width; Embedder validates it.
        response = client.models.embed_content(model=model, contents=list(texts))
        return [[float(value) for value in item.values] for item in response.embeddings]

    return transport


def live_image_transport(*, model: str, api_key: str | None = None) -> ImageTransport:
    """Build a live page-image transport; never called from tests or CI."""
    genai = _load_genai()
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def transport(data: bytes, mime_type: str) -> list[float]:
        part = genai.types.Part.from_bytes(data=data, mime_type=mime_type)
        response = client.models.embed_content(model=model, contents=[part])
        return [float(value) for value in response.embeddings[0].values]

    return transport


class GoogleGenaiLLM:
    """LLM port implementation with a deterministic offline default."""

    def __init__(self, *, transport: CompletionTransport | None = None) -> None:
        self._transport = transport if transport is not None else _offline_completion

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a completion, translating transport failures to ``PortError``."""
        if not prompt.strip():
            msg = "prompt must not be empty"
            raise ValidationError(msg, context={"prompt": prompt})
        try:
            result = self._transport(prompt, system)
        except PortError:
            raise
        except _sdk_error_types() as exc:
            msg = "google-genai completion failed"
            raise PortError(msg, context={"error": str(exc)}) from exc
        if not result.strip():
            msg = "google-genai returned an empty completion"
            raise PortError(msg)
        return result


class GoogleGenaiEmbedder:
    """Embedder port implementation with a deterministic offline default."""

    def __init__(self, *, dimension: int, transport: EmbeddingTransport | None = None) -> None:
        if dimension <= 0:
            msg = "dimension must be positive"
            raise ValidationError(msg, context={"dimension": dimension})
        self._dimension = dimension
        self._transport = transport if transport is not None else _offline_embedding

    @property
    def dimension(self) -> int:
        """Return the configured vector width."""
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch in order, enforcing the frozen port's width and value bounds."""
        try:
            vectors = self._transport(texts, self._dimension)
        except PortError:
            raise
        except _sdk_error_types() as exc:
            msg = "google-genai embedding failed"
            raise PortError(msg, context={"error": str(exc)}) from exc
        return _conform_vectors(
            vectors, dimension=self._dimension, count=len(texts), provider="google-genai"
        )


class GoogleGenaiPageImages:
    """Page-image handling entirely inside the adapter (L3, L15)."""

    def __init__(
        self,
        *,
        object_store: ObjectStore,
        dimension: int,
        transport: ImageTransport | None = None,
    ) -> None:
        if dimension <= 0:
            msg = "dimension must be positive"
            raise ValidationError(msg, context={"dimension": dimension})
        self._object_store = object_store
        self._dimension = dimension
        self._transport = (
            transport if transport is not None else _offline_image_transport(dimension)
        )

    def store_page(self, ref: ImageRef, data: bytes) -> str:
        """Store image bytes under the ImageRef key via the ObjectStore port."""
        return str(self._object_store.put(ref.ref_id, data, content_type=ref.mime_type))

    def embed_page(self, ref: ImageRef) -> list[float]:
        """Resolve image bytes through ObjectStore and embed them."""
        data = self._object_store.get(ref.ref_id)
        try:
            return self._transport(data, ref.mime_type)
        except PortError:
            raise
        except _sdk_error_types() as exc:
            msg = "google-genai page-image embedding failed"
            raise PortError(msg, context={"ref_id": ref.ref_id, "error": str(exc)}) from exc


__all__ = [
    "GoogleGenaiEmbedder",
    "GoogleGenaiLLM",
    "GoogleGenaiPageImages",
    "GoogleGenaiSDKError",
    "live_completion_transport",
    "live_embedding_transport",
    "live_image_transport",
]
