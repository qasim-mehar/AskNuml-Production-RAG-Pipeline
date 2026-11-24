"""Breadth-first URL frontier with a depth cap and canonical-URL dedup (L9)."""

from collections import deque
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from uni_rag_core.errors import ValidationError

_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})
_DEFAULT_PORTS: Final[dict[str, str]] = {"http": "80", "https": "443"}


def canonicalize_url(url: str) -> str:
    """Return a stable key for ``url``; drop fragment, default port and query order.

    Raises:
        ValidationError: if ``url`` is not an absolute HTTP(S) URL.
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES or not parts.netloc:
        msg = "seed must be an absolute HTTP(S) URL"
        raise ValidationError(msg, context={"url": url})

    netloc = parts.netloc.lower()
    default_port = _DEFAULT_PORTS[scheme]
    if netloc.endswith(f":{default_port}"):
        netloc = netloc[: -len(default_port) - 1]

    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"

    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((scheme, netloc, path, query, ""))


@dataclass(frozen=True)
class FrontierItem:
    """One queued URL and the depth at which it was discovered."""

    url: str
    depth: int
    canonical_url: str


class Frontier:
    """FIFO queue that admits each canonical URL at most once."""

    def __init__(self, seeds: list[str] | tuple[str, ...], *, max_depth: int) -> None:
        if max_depth < 0:
            msg = "max_depth must not be negative"
            raise ValidationError(msg, context={"max_depth": max_depth})
        self._max_depth = max_depth
        self._seen: set[str] = set()
        self._queue: deque[FrontierItem] = deque()
        for seed in seeds:
            self.add(seed, 0)

    def add(self, url: str, depth: int) -> bool:
        """Enqueue ``url`` if it is within the depth cap and not seen before."""
        canonical = canonicalize_url(url)
        if depth > self._max_depth or canonical in self._seen:
            return False
        self._seen.add(canonical)
        self._queue.append(FrontierItem(url=url, depth=depth, canonical_url=canonical))
        return True

    def requeue(self, item: FrontierItem) -> None:
        """Put a deferred item back without consuming its dedup slot."""
        self._queue.append(item)

    def pop(self) -> FrontierItem | None:
        """Return the next item, or ``None`` when the frontier is drained."""
        if not self._queue:
            return None
        return self._queue.popleft()

    @property
    def seen(self) -> frozenset[str]:
        """All canonical URLs admitted so far."""
        return frozenset(self._seen)

    def __len__(self) -> int:
        return len(self._queue)
