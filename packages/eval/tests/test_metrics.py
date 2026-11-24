"""Hand-computed oracle equality for every metric (L1/L4/L12)."""

from __future__ import annotations

from typing import Any

import pytest
from eval_helpers import StubRetriever, load_fixture

from uni_rag_eval.domain.golden import load_golden_set
from uni_rag_eval.domain.judge import FaithfulnessJudge, Judgment
from uni_rag_eval.domain.metrics import (
    abstention_precision,
    faithfulness,
    mean_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from uni_rag_eval.runner.harness import (
    FakeFaithfulnessLLM,
    LLMJudge,
    RunContext,
    default_judge,
    run_harness,
)


def test_recall_at_k_matches_hand_computed_oracle() -> None:
    retrieved = ["x", "b", "a", "c"]
    expected = ["a", "b"]
    assert recall_at_k(retrieved, expected, 1) == 0.0
    assert recall_at_k(retrieved, expected, 2) == 0.5
    assert recall_at_k(retrieved, expected, 3) == 1.0
    assert recall_at_k(retrieved, expected, 0) == 0.0
    assert recall_at_k(retrieved, [], 3) == 0.0


def test_mrr_matches_hand_computed_oracle() -> None:
    retrieved = ["x", "b", "a", "c"]
    expected = ["a", "b"]
    assert reciprocal_rank(retrieved, expected, 10) == 0.5
    assert reciprocal_rank(retrieved, expected, 1) == 0.0
    assert mean_reciprocal_rank([(retrieved, expected), (["d"], ["d"])], 10) == 0.75


def test_ndcg_at_k_matches_hand_computed_oracle() -> None:
    assert ndcg_at_k(["x", "b", "a", "c"], ["a", "b"], 3) == pytest.approx(0.693426, abs=1e-6)
    assert ndcg_at_k(["d"], ["d"], 1) == 1.0
    assert ndcg_at_k([], ["d"], 1) == 0.0


def test_faithfulness_matches_hand_computed_oracle() -> None:
    judge = default_judge()

    class FixedJudge:
        def judge(self, claim: str, evidence: list[str]) -> Judgment:
            return Judgment(entailed=claim == "yes", reason="fixed")

    fixed: FaithfulnessJudge = FixedJudge()
    assert faithfulness(["yes", "no"], ["evidence"], fixed) == 0.5
    assert faithfulness(["yes"], ["evidence"], fixed) == 1.0
    assert faithfulness([], ["evidence"], fixed) == 0.0
    assert faithfulness(["Alpha evidence"], ["Alpha evidence"], judge) == 1.0
    assert faithfulness(["Dr. Ayesha Khan"], ["Instructor: Dr. Ayesha Khan"], judge) == 1.0
    assert faithfulness(["اردو دعوی"], ["Instructor: Dr. Ayesha Khan"], judge) == 0.0


def test_fake_faithfulness_llm_uses_the_llm_port() -> None:
    from uni_rag_core import LLM

    llm = FakeFaithfulnessLLM()
    assert isinstance(llm, LLM)
    assert (
        llm.complete("Claim: Alpha evidence\nEvidence:\n- Alpha evidence\nReply YES or NO.")
        == "YES"
    )
    judge = LLMJudge(llm)
    assert judge.judge("Alpha evidence", ["Alpha evidence"]).entailed is True
    assert judge.judge("missing", ["Alpha evidence"]).entailed is False


def test_abstention_precision_matches_hand_computed_oracle() -> None:
    decisions = [(True, True), (True, False), (False, False), (False, True)]
    assert abstention_precision(decisions) == 0.5
    assert abstention_precision([(False, True)]) == 0.0
    assert abstention_precision([]) == 0.0


def _context(top_k: int) -> RunContext:
    return RunContext(
        run_id="oracle-test",
        backend="stub",
        corpus="synthetic-corpus-v1",
        variant_name="stub",
        chunking_strategy="awaiting-lane-c",
        golden_id="synthetic-oracle-v1",
        top_k=top_k,
        timestamp="2026-01-01T00:00:00+00:00",
    )


def _run(top_k: int) -> Any:
    golden = load_golden_set(load_fixture("synthetic-golden.json"))
    stub = StubRetriever(load_fixture("stub-answers.json")["answers"])
    return run_harness(golden, stub, default_judge(), _context(top_k))


def test_harness_reproduces_every_hand_computed_record_value() -> None:
    oracle = load_fixture("oracle-metrics.json")
    result = _run(3)
    for record_id, expected in oracle["per_record"].items():
        actual = result.per_record[record_id]
        assert actual.recall_at_k == pytest.approx(expected["recall_at_3"], abs=1e-6)
        assert actual.reciprocal_rank == pytest.approx(expected["mrr"], abs=1e-6)
        assert actual.ndcg == pytest.approx(expected["ndcg_at_3"], abs=1e-6)
        assert actual.faithfulness == pytest.approx(expected["faithfulness"], abs=1e-6)

    overall = oracle["overall"]
    assert result.overall.recall_at_k == pytest.approx(overall["recall_at_3"], abs=1e-6)
    assert result.overall.mrr == pytest.approx(overall["mrr"], abs=1e-6)
    assert result.overall.ndcg == pytest.approx(overall["ndcg_at_3"], abs=1e-6)
    assert result.overall.faithfulness == pytest.approx(overall["faithfulness"], abs=1e-6)
    assert result.overall.abstention_precision == pytest.approx(
        overall["abstention_precision"], abs=1e-6
    )


def test_recall_at_one_is_exactly_one_for_one_query_and_zero_for_another() -> None:
    result = _run(1)
    assert result.per_record["s1"].recall_at_k == 0.0
    assert result.per_record["s3"].recall_at_k == 1.0
