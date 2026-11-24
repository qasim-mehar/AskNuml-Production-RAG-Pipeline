"""Digit normalization shared by segmentation and metadata extraction (L7)."""

from __future__ import annotations

_ASCII_DIGITS = "01234567890123456789"
_NON_ASCII_DIGITS = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
_TRANSLATION = str.maketrans(_NON_ASCII_DIGITS, _ASCII_DIGITS)


def to_ascii_digits(text: str) -> str:
    """Map Persian/Arabic-Indic digits to ASCII without touching other code points."""
    return text.translate(_TRANSLATION)
