"""Deterministic in-memory LLM fake."""

from uni_rag_core.errors import ValidationError


class FakeLLM:
    """Returns a deterministic, prompt-derived completion. No network calls."""

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a stable completion string derived from the prompt."""
        if not prompt.strip():
            msg = "prompt must not be empty"
            raise ValidationError(msg, context={"prompt": prompt})
        prefix = f"{system.strip()} " if system and system.strip() else ""
        return f"{prefix}Fake answer: {prompt.strip()[:120]}"
