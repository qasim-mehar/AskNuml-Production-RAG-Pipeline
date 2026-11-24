"""Change-detection specs: idempotency, version bumps and soft marks."""

from uni_rag_ingestion.crawler.domain import ChangeDetector, content_hash


def test_content_hash_is_stable_for_identical_bytes() -> None:
    assert content_hash(b"same body") == content_hash(b"same body")
    assert content_hash(b"same body") != content_hash(b"other body")


def test_first_seen_hash_emits_version_one() -> None:
    decision = ChangeDetector().evaluate("https://example.edu/a", "hash-1")
    assert decision.emit is True
    assert decision.version == "1"
    assert decision.soft_mark is None


def test_unchanged_hash_produces_no_reemit_or_bump() -> None:
    detector = ChangeDetector()
    detector.evaluate("https://example.edu/a", "hash-1")
    decision = detector.evaluate("https://example.edu/a", "hash-1")
    assert decision.emit is False
    assert decision.version == "1"
    assert decision.soft_mark is None
    assert detector.version_of("https://example.edu/a") == "1"
    assert detector.soft_marked("https://example.edu/a") == ()


def test_changed_hash_bumps_version_and_soft_marks_old() -> None:
    detector = ChangeDetector()
    detector.evaluate("https://example.edu/a", "hash-1")
    decision = detector.evaluate("https://example.edu/a", "hash-2")
    assert decision.emit is True
    assert decision.version == "2"
    assert decision.previous_hash == "hash-1"
    assert decision.soft_mark is not None
    assert (decision.soft_mark.version, decision.soft_mark.content_hash) == ("1", "hash-1")
    assert [mark.version for mark in detector.soft_marked("https://example.edu/a")] == ["1"]
