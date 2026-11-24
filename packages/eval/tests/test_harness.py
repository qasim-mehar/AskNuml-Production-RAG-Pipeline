"""Harness mechanics: injection, determinism, language split and trace logging."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval_helpers import StubRetriever, load_fixture

from uni_rag_core import FakeClock, Language, Query
from uni_rag_eval.domain.golden import (
    chunks_from_registry,
    load_fixture_registry,
    load_golden_set,
)
from uni_rag_eval.domain.variant import DEFAULT_VARIANT
from uni_rag_eval.runner.ablation import variant_table_markdown
from uni_rag_eval.runner.harness import (
    RetrievalCallable,
    RunContext,
    build_fake_pipeline,
    default_judge,
    language_counts,
    run_harness,
)

ROOT = Path(__file__).resolve().parents[3]


def _stub_context() -> RunContext:
    return RunContext(
        run_id="determinism-test",
        backend="stub",
        corpus="synthetic-corpus-v1",
        variant_name="stub",
        chunking_strategy="awaiting-lane-c",
        golden_id="synthetic-oracle-v1",
        top_k=3,
        timestamp="2026-01-01T00:00:00+00:00",
    )


def _stub_run() -> Any:
    golden = load_golden_set(load_fixture("synthetic-golden.json"))
    stub = StubRetriever(load_fixture("stub-answers.json")["answers"])
    return run_harness(golden, stub, default_judge(), _stub_context())


def _fake_run() -> Any:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    pipeline = build_fake_pipeline(
        chunks_from_registry(registry), variant=DEFAULT_VARIANT, clock=FakeClock()
    )
    context = RunContext(
        run_id="fake-test",
        backend="fake",
        corpus=registry.registry_id,
        variant_name=DEFAULT_VARIANT.name,
        chunking_strategy=DEFAULT_VARIANT.chunking_strategy,
        golden_id=golden.golden_id,
        top_k=5,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    return run_harness(golden, pipeline, default_judge(), context)


def test_retrieval_callable_is_injected_as_a_protocol() -> None:
    golden = load_golden_set(load_fixture("synthetic-golden.json"))
    stub = StubRetriever(load_fixture("stub-answers.json")["answers"])
    fake_pipeline = build_fake_pipeline([], variant=DEFAULT_VARIANT, clock=FakeClock())
    assert isinstance(stub, RetrievalCallable)
    assert isinstance(fake_pipeline, RetrievalCallable)
    assert isinstance(stub(Query(query_id="s1", text="alpha", language=Language.EN)), object)
    assert run_harness(golden, stub, default_judge(), _stub_context()).overall.n_records == 4
    assert _fake_run().overall.n_records == 30


def test_identical_inputs_produce_identical_scores_and_tables() -> None:
    first = _stub_run()
    second = _stub_run()
    assert asdict(first) == asdict(second)
    assert variant_table_markdown(first) == variant_table_markdown(second)

    fake_first = _fake_run()
    fake_second = _fake_run()
    assert asdict(fake_first) == asdict(fake_second)
    assert variant_table_markdown(fake_first) == variant_table_markdown(fake_second)


def test_per_language_scores_are_present_and_visible_in_tables() -> None:
    result = _stub_run()
    assert set(result.scores_by_language) == {"en", "ur", "roman_urdu"}
    table = variant_table_markdown(result)
    for language in ("| en |", "| ur |", "| roman_urdu |", "| overall |"):
        assert language in table


def test_run_logs_configuration_and_trace_ids(caplog: Any) -> None:
    with caplog.at_level(logging.INFO):
        result = _stub_run()
    config_records = [record for record in caplog.records if record.message == "eval.run.complete"]
    assert len(config_records) == 1
    assert config_records[0].trace_id
    assert config_records[0].extra_fields["fingerprint"] == result.context.fingerprint()
    assert {trace.trace_id for trace in result.traces} == {
        hashlib.sha256(f"{result.context.run_id}:{record.id}".encode()).hexdigest()[:32]
        for record in load_golden_set(load_fixture("synthetic-golden.json")).records
    }


def test_language_counts_cover_every_golden_record() -> None:
    golden = load_golden_set(load_fixture("synthetic-golden.json"))
    assert sum(language_counts(golden).values()) == len(golden.records)
