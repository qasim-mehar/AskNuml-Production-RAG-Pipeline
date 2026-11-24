# mypy: disable-error-code=import-untyped
"""Second provider adapter: OpenAI (also usable with a local OpenAI-compatible server).

Chosen because its chat-completions and embeddings endpoints expose exactly the
``LLM`` and ``Embedder`` port surfaces, so the same shared contract suite runs
unchanged (L17). ``base_url`` allows the same adapter to target a local server
without new core ports. The SDK is imported lazily; offline transports are
deterministic and are the only ones exercised in CI (ADR 0002, L4, L15).
"""

from __future__ import annotations

import hashlib
import importlib
import math
from collections.abc import Callable, Sequence
from typing import Any

from uni_rag_core import PortError, ValidationError

CompletionTransport = Callable[[str, str | None], str]
EmbeddingTransport = Callable[[Sequence[str], int], list[list[float]]]


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
    return f"{prefix}openai[offline]: {prompt.strip()[:120]}"


def _offline_embedding(texts: Sequence[str], dimension: int) -> list[list[float]]:
    return [_hash_vector(f"openai:{text}".encode(), dimension) for text in texts]


def _load_openai() -> Any:
    """Import the SDK only when live mode is explicitly constructed."""
    try:
        return importlib.import_module("openai")
    except ImportError as exc:
        msg = "openai is not installed; enable the 'openai' extra for live mode"
        raise PortError(msg, context={"extra": "openai"}) from exc


def live_completion_transport(
    *,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
) -> CompletionTransport:
    """Build a live completion transport; never called from tests or CI."""
    sdk = _load_openai()
    client = sdk.OpenAI(api_key=api_key, base_url=base_url)

    def transport(prompt: str, system: str | None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=model, messages=messages)
        return str(response.choices[0].message.content or "")

    return transport


def live_embedding_transport(
    *,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
) -> EmbeddingTransport:
    """Build a live embedding transport; never called from tests or CI."""
    sdk = _load_openai()
    client = sdk.OpenAI(api_key=api_key, base_url=base_url)

    def transport(texts: Sequence[str], dimension: int) -> list[list[float]]:
        del dimension  # The remote model fixes its own width; Embedder validates it.
        response = client.embeddings.create(model=model, input=list(texts))
        return [[float(value) for value in item.embedding] for item in response.data]

    return transport


class OpenAILLM:
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
        except Exception as exc:
            msg = "openai completion failed"
            raise PortError(msg, context={"error": str(exc)}) from exc
        if not result.strip():
            msg = "openai returned an empty completion"
            raise PortError(msg)
        return result


class OpenAIEmbedder:
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
        except Exception as exc:
            msg = "openai embedding failed"
            raise PortError(msg, context={"error": str(exc)}) from exc
        return _conform_vectors(
            vectors, dimension=self._dimension, count=len(texts), provider="openai"
        )


__all__ = [
    "OpenAIEmbedder",
    "OpenAILLM",
    "live_completion_transport",
    "live_embedding_transport",
]
