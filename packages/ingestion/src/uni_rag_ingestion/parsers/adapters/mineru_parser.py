"""MinerU adapter interface for scanned past-paper pages (ADR-0003, L3).

MinerU is parked in this environment: no installable wheel is available and
no OCR result is fabricated. The interface is ready for a real engine; tests
use a checked-in *transcription* sidecar, which is labeled ground truth and
explicitly not OCR output. The scanned PNG itself supplies the page image.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from uni_rag_core.errors import ParseError
from uni_rag_core.logging import get_logger
from uni_rag_ingestion.parsers.domain.models import ParsedDocument, ParsedPage

_logger = get_logger("uni_rag.parsers.mineru")


@runtime_checkable
class MinerUEngine(Protocol):
    """Minimal surface required from a real MinerU engine."""

    def parse(self, source_path: Path) -> str:
        """Return the page transcription produced by MinerU."""
        ...


class MinerUParser:
    """Parse a scanned page using an injected MinerU engine or a fixture transcription.

    Args:
        engine: a real MinerU engine, when one is available.
        transcription_path: checked-in transcription used only for fixtures.
            It is ground-truth text, not an OCR result.
    """

    def __init__(
        self,
        *,
        engine: MinerUEngine | None = None,
        transcription_path: Path | None = None,
    ) -> None:
        self._engine = engine
        self._transcription_path = transcription_path

    def parse(self, source_path: Path) -> ParsedDocument:
        """Parse ``source_path`` into a single-page document with raw image bytes.

        Raises:
            ParseError: if the image cannot be read, no engine is configured,
                or the transcription cannot be read. The source path is always
                recorded in the error context (L10/L11).
        """
        try:
            image = source_path.read_bytes()
            if self._engine is not None:
                text = self._engine.parse(source_path)
            elif self._transcription_path is not None:
                _logger.warning(
                    "mineru.parked",
                    source_path=str(source_path),
                    fallback="fixture-transcription",
                )
                text = self._transcription_path.read_text(encoding="utf-8")
            else:
                raise ParseError(
                    "MinerU engine is unavailable and no fixture transcription was supplied",
                    context={"source_path": str(source_path)},
                )
        except ParseError:
            raise
        except (OSError, UnicodeError) as exc:
            raise ParseError(
                "could not parse scanned page",
                context={"source_path": str(source_path)},
            ) from exc

        return ParsedDocument(
            pages=(ParsedPage(page=1, text=text, image=image),),
        )
