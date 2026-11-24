"""Pure past-paper question segmentation (L9).

Numbering markers are consumed structurally; all other text is preserved
verbatim, including Urdu code points (L7).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain._digits import to_ascii_digits
from uni_rag_ingestion.parsers.domain.models import ParsedPage, QuestionSpan

_QUESTION_RE = re.compile(
    r"^\s*(?:Q\s*\.?\s*|سوال\s+)?([0-9۰-۹٠-٩]+)\s*[\.\):\-]\s*(.*)$",
    re.IGNORECASE,
)
_OPTION_RE = re.compile(r"^\s*(?:\((?P<a>[a-dA-D])\)|(?P<b>[a-dA-D])[\.\):])\s+(?P<text>.+)$")


def segment_questions(pages: Sequence[ParsedPage]) -> tuple[QuestionSpan, ...]:
    """Split ordered pages into one :class:`QuestionSpan` per question.

    Continuation lines and option lines attach to the open question; a repeated
    marker number is treated as a continuation, not a second record.

    Raises:
        ParseError: when no question marker is found anywhere in ``pages``.
    """
    spans: list[QuestionSpan] = []
    current: QuestionSpan | None = None

    for page in pages:
        for raw_line in page.text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = _QUESTION_RE.match(line)
            if match is not None:
                number = int(to_ascii_digits(match.group(1)))
                if current is not None and number == current.question_number:
                    joined = f"{current.text}\n{line}" if current.text else line
                    current = QuestionSpan(
                        question_number=current.question_number,
                        text=joined,
                        page=current.page,
                        options=current.options,
                    )
                    continue
                if current is not None:
                    spans.append(current)
                current = QuestionSpan(
                    question_number=number,
                    text=match.group(2).strip(),
                    page=page.page,
                )
                continue
            if current is None:
                continue
            option = _OPTION_RE.match(line)
            if option is not None:
                label = option.group("a") or option.group("b")
                entry = f"{label}) {option.group('text')}"
                current = QuestionSpan(
                    question_number=current.question_number,
                    text=current.text,
                    page=current.page,
                    options=current.options + (entry,),
                )
            else:
                joined = f"{current.text}\n{line}" if current.text else line
                current = QuestionSpan(
                    question_number=current.question_number,
                    text=joined,
                    page=current.page,
                    options=current.options,
                )

    if current is not None:
        spans.append(current)
    if not spans:
        raise ParseError(
            "no question markers found in past-paper text",
            context={"pages": len(pages)},
        )
    return tuple(spans)
