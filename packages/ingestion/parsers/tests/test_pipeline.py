"""End-to-end pipeline pins: records, page images, Urdu, determinism, typed errors."""

import json
from datetime import UTC, datetime
from typing import cast

import pytest
from _helpers import document_for, load_spec, parser_for, resolve_fixture

from uni_rag_core import DocType, Document, Language
from uni_rag_core.errors import ParseError, StorageError
from uni_rag_core.fakes.object_store import FakeObjectStore
from uni_rag_ingestion.parsers.adapters.docling_parser import DoclingEngine, DoclingParser
from uni_rag_ingestion.parsers.adapters.mineru_parser import MinerUParser
from uni_rag_ingestion.parsers.domain.models import ParsedDocument
from uni_rag_ingestion.parsers.service.parse import parse_document

_SPECS = [
    "digital-past-paper.json",
    "digital-past-paper-html.json",
    "urdu-past-paper.json",
    "scanned-past-paper.json",
]


@pytest.mark.parametrize("spec_name", _SPECS)
def test_pipeline_emits_exactly_the_labeled_records_with_provenance(spec_name: str) -> None:
    spec = load_spec(spec_name)
    store = FakeObjectStore()
    outcome = parse_document(
        document_for(spec),
        source_path=resolve_fixture(spec.source_path),
        parser=parser_for(spec),
        object_store=store,
    )
    assert len(outcome.questions) == len(spec.expected_questions)
    assert set(outcome.image_refs) == set(range(1, spec.expected_page_count + 1))
    for page, ref in outcome.image_refs.items():
        assert ref.ref_id == f"parsed-images/{spec.doc_id}/p{page}.png"
        assert ref.page == page
        assert ref.source_url == spec.source_url
        assert store.get(ref.ref_id)
    for question, expected in zip(outcome.questions, spec.expected_questions, strict=True):
        assert (question.question_number, question.page, question.text, question.options) == (
            expected.question_number,
            expected.page,
            expected.text,
            expected.options,
        )
        assert question.doc_id == spec.doc_id
        assert question.source_url == spec.source_url
        assert question.year == spec.expected_metadata.year
        assert question.subject == spec.expected_metadata.course_code
        assert question.image_ref is not None
        assert question.image_ref.page == question.page
        assert question.image_ref.ref_id in {ref.ref_id for ref in outcome.image_refs.values()}


def test_scanned_page_image_bytes_are_persisted_through_object_store() -> None:
    spec = load_spec("scanned-past-paper.json")
    store = FakeObjectStore()
    outcome = parse_document(
        document_for(spec),
        source_path=resolve_fixture(spec.source_path),
        parser=parser_for(spec),
        object_store=store,
    )
    assert spec.image_source is not None
    ref = outcome.image_refs[1]
    assert store.get(ref.ref_id) == resolve_fixture(spec.image_source).read_bytes()
    assert ref.caption == "scanned past-paper page"
    assert store.content_type_of(ref.ref_id) == "image/png"


def test_urdu_question_text_round_trips_byte_for_byte() -> None:
    for spec_name in ("urdu-past-paper.json", "scanned-past-paper.json"):
        spec = load_spec(spec_name)
        outcome = parse_document(
            document_for(spec),
            source_path=resolve_fixture(spec.source_path),
            parser=parser_for(spec),
            object_store=FakeObjectStore(),
        )
        expected = [q.text.encode("utf-8") for q in spec.expected_questions]
        actual = [q.text.encode("utf-8") for q in outcome.questions]
        assert actual == expected


def test_reparsing_the_same_fixture_produces_byte_identical_records() -> None:
    spec = load_spec("digital-past-paper.json")

    def run() -> tuple[str, dict[str, bytes]]:
        store = FakeObjectStore()
        outcome = parse_document(
            document_for(spec),
            source_path=resolve_fixture(spec.source_path),
            parser=parser_for(spec),
            object_store=store,
        )
        records = json.dumps(
            [question.model_dump(mode="json") for question in outcome.questions],
            ensure_ascii=False,
            sort_keys=True,
        )
        images = {ref.ref_id: store.get(ref.ref_id) for ref in outcome.image_refs.values()}
        return records, images

    assert run() == run()


def test_malformed_document_raises_typed_error_naming_the_source() -> None:
    source = resolve_fixture("../pdf/digital-course-outline.pdf")
    document = Document(
        doc_id="paper-course-outline",
        source_url="https://example.edu/courses/cs101",
        title="CS-101 Course Outline",
        doc_type=DocType.PDF,
        last_crawled=datetime(2026, 1, 1, tzinfo=UTC),
        content_hash="hash-course-outline",
        language=Language.EN,
    )
    with pytest.raises(ParseError) as raised:
        parse_document(
            document,
            source_path=source,
            parser=DoclingParser(prefer_docling=False),
            object_store=FakeObjectStore(),
        )
    assert raised.value.context["source_path"] == str(source)
    assert set(raised.value.context["missing_fields"]) == {
        "year",
        "term",
        "exam_type",
        "department",
    }


def test_missing_source_raises_typed_error_instead_of_silently_skipping() -> None:
    spec = load_spec("digital-past-paper.json")
    missing = resolve_fixture("does-not-exist.pdf", must_exist=False)
    with pytest.raises(ParseError) as raised:
        parse_document(
            document_for(spec),
            source_path=missing,
            parser=DoclingParser(prefer_docling=False),
            object_store=FakeObjectStore(),
        )
    assert raised.value.context["source_path"] == str(missing)


def test_mineru_parser_without_engine_or_transcription_raises_typed_error() -> None:
    source = resolve_fixture("../pdf/scanned-past-paper-page.png")
    with pytest.raises(ParseError) as raised:
        MinerUParser().parse(source)
    assert raised.value.context["source_path"] == str(source)


class _FailingStore:
    def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        raise StorageError("object store is unavailable", context={"key": key})

    def get(self, key: str) -> bytes:
        raise StorageError("object store is unavailable", context={"key": key})

    def delete(self, key: str) -> None:
        return None


def test_object_store_failure_becomes_a_parse_error_naming_the_source() -> None:
    spec = load_spec("digital-past-paper.json")
    source = resolve_fixture(spec.source_path)
    with pytest.raises(ParseError) as raised:
        parse_document(
            document_for(spec),
            source_path=source,
            parser=parser_for(spec),
            object_store=_FailingStore(),
        )
    assert raised.value.context["source_path"] == str(source)
    assert raised.value.context["key"] == f"parsed-images/{spec.doc_id}/p1.png"


class _BrokenTable:
    def export_to_dict(self) -> dict[str, object]:
        return {"bad": "shape"}


class _BrokenDocument:
    @property
    def pages(self) -> list[object]:
        return []

    @property
    def tables(self) -> list[_BrokenTable]:
        return [_BrokenTable()]


class _BrokenResult:
    @property
    def document(self) -> _BrokenDocument:
        return _BrokenDocument()


class _BrokenEngine:
    def convert(self, source: str) -> _BrokenResult:
        return _BrokenResult()


def test_docling_table_failure_is_typed_and_names_the_source() -> None:
    source = resolve_fixture("digital-past-paper.html")
    with pytest.raises(ParseError) as raised:
        DoclingParser(engine=cast(DoclingEngine, _BrokenEngine())).parse(source)
    assert raised.value.context["source_path"] == str(source)


class _FakeTable:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def export_to_dict(self) -> dict[str, object]:
        return self.data


class _FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def export_to_text(self) -> str:
        return self.text


class _FakeDocument:
    @property
    def pages(self) -> list[_FakePage]:
        return [_FakePage("CS-101 MIDTERM EXAMINATION"), _FakePage("Q1. alpha")]

    @property
    def tables(self) -> list[_FakeTable]:
        return [_FakeTable({"page": 1, "header": ["Field"], "rows": [["Value"]]})]


class _FakeResult:
    @property
    def document(self) -> _FakeDocument:
        return _FakeDocument()


class _FakeEngine:
    def convert(self, source: str) -> _FakeResult:
        return _FakeResult()


def test_docling_engine_path_maps_pages_and_tables_without_the_library() -> None:
    engine: DoclingEngine = _FakeEngine()
    parsed: ParsedDocument = DoclingParser(engine=engine).parse(
        resolve_fixture("digital-past-paper.html")
    )
    assert [page.page for page in parsed.pages] == [1, 2]
    assert [page.text for page in parsed.pages] == [
        "CS-101 MIDTERM EXAMINATION",
        "Q1. alpha",
    ]
    assert parsed.pages[0].tables[0].header == ("Field",)
    assert parsed.pages[0].tables[0].rows == (("Value",),)


def test_fixture_placeholder_image_is_explicitly_captioned() -> None:
    spec = load_spec("digital-past-paper.json")
    outcome = parse_document(
        document_for(spec),
        source_path=resolve_fixture(spec.source_path),
        parser=parser_for(spec),
        object_store=FakeObjectStore(),
    )
    assert all(
        ref.caption == "placeholder page image (no renderer available)"
        for ref in outcome.image_refs.values()
    )
