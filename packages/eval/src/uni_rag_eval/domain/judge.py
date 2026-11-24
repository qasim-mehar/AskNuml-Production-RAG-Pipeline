"""Faithfulness judging protocol, deterministic verdict parsing and prompts.

The default judge uses the core ``LLM`` port with a deterministic fake LLM, so
no scoring path needs a network call or wall-clock (L1/L3/L4).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from uni_rag_core.errors import ValidationError

_CLAIM_PREFIX = "Claim: "
_EVIDENCE_HEADER = "Evidence:"
_REPLY_LINE = "Reply YES or NO."
_TOKEN = re.compile(r"\w+", flags=re.UNICODE)

FAITHFULNESS_SYSTEM_PROMPT = (
    "You are a strict faithfulness judge. Decide whether every fact in the claim is "
    "supported by the evidence. Reply with exactly YES or exactly NO and nothing else."
)


@dataclass(frozen=True)
class Judgment:
    """A judge's binary entailment decision and a short, human-readable reason."""

    entailed: bool
    reason: str


@runtime_checkable
class FaithfulnessJudge(Protocol):
    """Domain-local judging protocol (L3): claim + evidence to a binary verdict."""

    def judge(self, claim: str, evidence: Sequence[str]) -> Judgment:
        """Return whether ``claim`` is entailed by ``evidence``."""
        ...


def build_faithfulness_prompt(claim: str, evidence: Sequence[str]) -> str:
    """Render the judge prompt; the format is parsed back by the deterministic fake."""
    lines = [_CLAIM_PREFIX + claim.strip(), _EVIDENCE_HEADER]
    lines.extend(f"- {item.strip()}" for item in evidence)
    lines.append(_REPLY_LINE)
    return "\n".join(lines)


def parse_faithfulness_prompt(prompt: str) -> tuple[str, tuple[str, ...]]:
    """Recover claim and evidence from a prompt built by :func:`build_faithfulness_prompt`."""
    lines = prompt.splitlines()
    if (
        len(lines) < 3
        or not lines[0].startswith(_CLAIM_PREFIX)
        or lines[1] != _EVIDENCE_HEADER
        or lines[-1] != _REPLY_LINE
    ):
        raise ValidationError("Malformed faithfulness prompt", context={"prompt": prompt[:120]})
    claim = lines[0][len(_CLAIM_PREFIX) :]
    evidence = tuple(line[2:] for line in lines[2:-1] if line.startswith("- "))
    if not claim or not evidence:
        raise ValidationError(
            "Faithfulness prompt needs a claim and at least one evidence item",
            context={"prompt": prompt[:120]},
        )
    return claim, evidence


def parse_verdict(completion: str) -> Judgment:
    """Parse a strict YES/NO completion; unparseable output is an error, not a silent pass."""
    verdict = completion.strip().upper()
    if verdict == "YES":
        return Judgment(entailed=True, reason="judge returned YES")
    if verdict == "NO":
        return Judgment(entailed=False, reason="judge returned NO")
    raise ValidationError(
        "Faithfulness judge returned an uninterpretable verdict",
        context={"completion": completion[:120]},
    )


def lexical_entailment(claim: str, evidence: Sequence[str]) -> bool:
    """Deterministic fake entailment: every claim token must appear in the evidence."""
    claim_tokens = set(_TOKEN.findall(claim.lower()))
    if not claim_tokens:
        return False
    evidence_tokens = set(_TOKEN.findall(" ".join(evidence).lower()))
    return claim_tokens <= evidence_tokens


def is_faithfulness_prompt(prompt: str) -> bool:
    """Return whether ``prompt`` was rendered by :func:`build_faithfulness_prompt`."""
    lines = prompt.splitlines()
    return bool(lines) and lines[0].startswith(_CLAIM_PREFIX) and lines[-1] == _REPLY_LINE
