"""Content-hash change detection and version soft-marking (L1, L9)."""

from dataclasses import dataclass, field
from hashlib import sha256


def content_hash(body: bytes) -> str:
    """Return the SHA-256 hex digest of ``body`` (stable across runs)."""
    return sha256(body).hexdigest()


@dataclass(frozen=True)
class SoftMark:
    """A prior version that has been superseded but not deleted."""

    url: str
    version: str
    content_hash: str


@dataclass(frozen=True)
class ChangeDecision:
    """Whether to emit a document and how to version it."""

    emit: bool
    version: str
    previous_hash: str | None
    soft_mark: SoftMark | None


@dataclass
class _UrlState:
    digest: str
    version: int
    superseded: list[SoftMark] = field(default_factory=list)


class ChangeDetector:
    """Per-URL hash registry: unchanged bodies are not re-emitted."""

    def __init__(self) -> None:
        self._states: dict[str, _UrlState] = {}

    def evaluate(self, canonical_url: str, digest: str) -> ChangeDecision:
        """Compare ``digest`` with the last seen digest for ``canonical_url``."""
        state = self._states.get(canonical_url)
        if state is None:
            self._states[canonical_url] = _UrlState(digest=digest, version=1)
            return ChangeDecision(emit=True, version="1", previous_hash=None, soft_mark=None)
        if state.digest == digest:
            return ChangeDecision(
                emit=False, version=str(state.version), previous_hash=digest, soft_mark=None
            )

        soft_mark = SoftMark(
            url=canonical_url, version=str(state.version), content_hash=state.digest
        )
        state.superseded.append(soft_mark)
        previous_hash = state.digest
        state.digest = digest
        state.version += 1
        return ChangeDecision(
            emit=True, version=str(state.version), previous_hash=previous_hash, soft_mark=soft_mark
        )

    def version_of(self, canonical_url: str) -> str | None:
        """Return the current version string for a URL, if it has been seen."""
        state = self._states.get(canonical_url)
        return str(state.version) if state is not None else None

    def soft_marked(self, canonical_url: str) -> tuple[SoftMark, ...]:
        """Return the superseded versions of ``canonical_url`` in bump order."""
        state = self._states.get(canonical_url)
        return tuple(state.superseded) if state is not None else ()
