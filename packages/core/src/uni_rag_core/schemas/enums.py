"""Controlled vocabularies shared by every contract."""

from enum import StrEnum


class DocType(StrEnum):
    """Origin of a document."""

    WEB_PAGE = "web_page"
    PDF = "pdf"
    PAST_PAPER = "past_paper"
    OTHER = "other"


class Language(StrEnum):
    """Supported query/document languages (L7)."""

    EN = "en"
    UR = "ur"
    ROMAN_URDU = "roman_urdu"
