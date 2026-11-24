"""Language-neutral, deterministic token estimate and split budgets (L4, L7).

Choice (documented for Lane F): a pinned whitespace/length heuristic. A token
is a whitespace-delimited unit, with a character-length floor so scripts with
little or no whitespace are not undercounted. No tokenizer dependency is added
(and therefore no Lane 0 ADR is requested). The same function drives both
strategies, so an ablation isolates the split policy, not the counter.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

TARGET_MIN = 300
TARGET_MAX = 500

_WHITESPACE_RUN = re.compile(r"\s+|\S+")
_SENTENCE_END = re.compile(r"(?<=[.!?۔؟])\s+")


def estimate_tokens(text: str) -> int:
    """Estimate token count from whitespace units and a character floor.

    The floor is ``ceil(non-whitespace characters / 4)``. Both terms are
    script-agnostic; Urdu, Roman Urdu and English all use whitespace between
    words, and the floor protects scripts that do not.
    """
    words = text.split()
    by_words = len(words)
    by_chars = math.ceil(sum(len(word) for word in words) / 4)
    return max(by_words, by_chars)


def word_units(text: str) -> list[str]:
    """Split into alternating whitespace/non-whitespace runs, losslessly.

    Re-joining the returned units reproduces ``text`` exactly. No English-only
    sentence rule is applied here (L7).
    """
    return _WHITESPACE_RUN.findall(text)


def sentence_units(text: str) -> list[str]:
    """Split at Latin or Urdu sentence marks, normalising boundary whitespace.

    Sentence text is kept verbatim; only whitespace at a boundary becomes one
    space, so word order and characters survive (L7). Oversized units are split
    further by the strategy via :func:`word_units`.
    """
    parts = _SENTENCE_END.split(text)
    return [part.strip() + " " for part in parts if part.strip()]


def body_budget(prefix: str) -> tuple[int, int]:
    """Return (min, max) body tokens for a chunk with the given prefix.

    The prefix (heading path and, for atomic units, a reason line) is charged
    against the 300-500 band so the final rendered text stays in band.
    """
    cost = estimate_tokens(prefix)
    return max(1, TARGET_MIN - cost), max(1, TARGET_MAX - cost)


def pack_units(units: Sequence[str], max_tokens: int) -> tuple[str, ...]:
    """Greedily pack units into windows of at most ``max_tokens``.

    Windows are emitted in input order. A trailing window below the band is
    marked atomic by the caller, never silently dropped. Deterministic and
    independent of dict/hash ordering (L4).
    """
    windows: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for unit in units:
        unit_tokens = estimate_tokens(unit)
        if current and current_tokens + unit_tokens > max_tokens:
            windows.append("".join(current).strip())
            current, current_tokens = [], 0
        current.append(unit)
        current_tokens += unit_tokens
    if current:
        windows.append("".join(current).strip())
    return tuple(windows)
