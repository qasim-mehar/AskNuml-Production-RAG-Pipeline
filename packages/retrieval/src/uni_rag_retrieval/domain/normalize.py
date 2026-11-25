"""Pure text normalization for English, Urdu and Roman Urdu (L7, L9).

Normalization has no I/O and is idempotent: folding twice is identical to
folding once. Roman-Urdu token folding is opt-in per call so the same function
serves English corpus text without corrupting it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from uni_rag_core.schemas import Language

_TOKEN = re.compile(r"\w+", flags=re.UNICODE)

# Arabic-Indic and Extended Arabic-Indic digits -> ASCII digits.
_CHAR_FOLDS: dict[int, str] = {
    **{codepoint: str(offset) for offset, codepoint in enumerate(range(0x0660, 0x066A))},
    **{codepoint: str(offset) for offset, codepoint in enumerate(range(0x06F0, 0x06FA))},
    0x0622: "\u0627",  # آ -> ا
    0x0623: "\u0627",  # أ -> ا
    0x0625: "\u0627",  # إ -> ا
    0x0671: "\u0627",  # ٱ -> ا
    0x0640: "",  # tatweel is presentation-only
    0x06D2: "\u06d3",  # ۓ -> ے
}

# Conservative Roman-Urdu spellings. Every target is deliberately *not* a key,
# which is what makes the fold idempotent.
_ROMAN_FOLDS: dict[str, str] = {
    "kaun": "kon",
    "kay": "ke",
    "kaa": "ka",
    "kya": "kia",
    "hae": "he",
    "hein": "hain",
    "sae": "se",
    "ktna": "kitna",
    "kitny": "kitne",
}

# A Roman-Urdu query needs at least two of these tokens; a single "ka" in an
# English sentence is not enough to change its language classification.
_ROMAN_MARKERS: frozenset[str] = frozenset(
    {
        "ka",
        "kaun",
        "kon",
        "kya",
        "kia",
        "hai",
        "he",
        "hain",
        "kab",
        "ktna",
        "kitna",
        "kitne",
        "kay",
        "ke",
        "mein",
        "main",
        "se",
        "sae",
        "aur",
        "ty",
        "tha",
        "thi",
        "hae",
        "ko",
    }
)

_URDU_RANGES: tuple[tuple[int, int], ...] = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def is_urdu_script(text: str) -> bool:
    """Return True when ``text`` contains Urdu/Arabic-script characters."""
    return any(start <= ord(char) <= end for char in text for start, end in _URDU_RANGES)


def looks_roman_urdu(tokens: Sequence[str]) -> bool:
    """Return True when at least two tokens are Roman-Urdu markers."""
    return sum(token in _ROMAN_MARKERS for token in tokens) >= 2


def normalize(text: str, *, language: Language | None = None) -> str:
    """Fold script, diacritics, digit forms, case and whitespace.

    ``language`` selects optional Roman-Urdu token folding; other languages use
    the shared script/case fold only. The result is stable under a second call
    with the same ``language``.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    folded = without_marks.translate(_CHAR_FOLDS)
    value = unicodedata.normalize("NFKC", folded).lower()
    if language is Language.ROMAN_URDU:
        value = " ".join(_ROMAN_FOLDS.get(token, token) for token in _TOKEN.findall(value))
    return re.sub(r"\s+", " ", value).strip()


def tokens(text: str, *, language: Language | None = None) -> list[str]:
    """Return normalized word tokens in original order."""
    return _TOKEN.findall(normalize(text, language=language))
