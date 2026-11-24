"""Shared fixture loading for the parsing lane tests."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from uni_rag_core import Document
from uni_rag_ingestion.parsers.adapters.docling_parser import DoclingParser
from uni_rag_ingestion.parsers.adapters.mineru_parser import MinerUParser
from uni_rag_ingestion.parsers.domain.models import DocumentParser
from uni_rag_ingestion.parsers.service.evaluate import FixtureSpec

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "pastpapers"
_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def load_spec(name: str) -> FixtureSpec:
    """Load one labeled ground-truth fixture by expected-file name."""
    raw = (FIXTURE_ROOT / "expected" / name).read_text(encoding="utf-8")
    return FixtureSpec.model_validate_json(raw)


def resolve_fixture(value: str, *, must_exist: bool = True) -> Path:
    """Resolve a fixture path relative to the corpus root or repository root."""
    direct = FIXTURE_ROOT / value
    if direct.exists():
        return direct
    repository_relative = FIXTURE_ROOT.parents[2] / value
    if repository_relative.exists():
        return repository_relative
    if not must_exist:
        return repository_relative
    raise FileNotFoundError(value)


def document_for(spec: FixtureSpec) -> Document:
    """Build a frozen Document from a labeled fixture (L5/L6)."""
    return Document(
        doc_id=spec.doc_id,
        source_url=spec.source_url,
        title=spec.title,
        doc_type=spec.doc_type,
        last_crawled=_FIXED_TIME,
        content_hash=hashlib.sha256(resolve_fixture(spec.source_path).read_bytes()).hexdigest(),
        language=spec.language,
    )


def parser_for(spec: FixtureSpec) -> DocumentParser:
    """Select the parser named by a labeled fixture."""
    if spec.source_kind.startswith("docling-"):
        return DoclingParser(prefer_docling=False)
    if spec.source_kind == "mineru-transcription":
        assert spec.transcription_path is not None
        return MinerUParser(transcription_path=resolve_fixture(spec.transcription_path))
    raise AssertionError(f"unexpected source kind: {spec.source_kind}")
