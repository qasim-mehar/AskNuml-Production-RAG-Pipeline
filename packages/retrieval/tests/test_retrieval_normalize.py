"""Pure normalization specs with coverage in all three languages (L7, L9)."""

from __future__ import annotations

import pytest

from uni_rag_core import Language
from uni_rag_retrieval.domain.normalize import normalize, tokens

_CASES: list[tuple[str, Language | None]] = [
    ("Who is the instructor for CS-101?", Language.EN),
    ("CS-101 کے انسٹرکٹر کون ہیں؟", Language.UR),
    ("CS-101 ka instructor kaun hai?", Language.ROMAN_URDU),
]


@pytest.mark.parametrize(("text", "language"), _CASES)
def test_normalization_is_pure_and_idempotent(text: str, language: Language | None) -> None:
    once = normalize(text, language=language)
    assert once == normalize(text, language=language)
    assert once == normalize(once, language=language)


def test_urdu_script_folds_digits_diacritics_and_alef_variants() -> None:
    folded = normalize("CS-۱۰۱ کے أنسٹرکٹر")
    assert "101" in folded
    assert "ا" in folded
    assert normalize("آ") == "ا"
    assert normalize("أ") == "ا"


def test_roman_urdu_folding_is_opt_in_and_idempotent() -> None:
    folded = normalize("CS-101 kaun kya hai?", language=Language.ROMAN_URDU)
    assert folded == "cs 101 kon kia hai"
    assert normalize(folded, language=Language.ROMAN_URDU) == folded
    assert normalize("kaun", language=Language.EN) == "kaun"


def test_tokens_preserve_order_without_punctuation() -> None:
    assert tokens("CS-101 ka instructor", language=Language.ROMAN_URDU) == [
        "cs",
        "101",
        "ka",
        "instructor",
    ]
