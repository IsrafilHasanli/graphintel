"""LLM provider abstraction.

Two providers:
  * deterministic (default) - no network; templated/rule outputs so extraction
    and answer generation are reproducible and testable offline.
  * anthropic - uses the Claude API when LLM_PROVIDER=anthropic and a key is set.

Prompts are versioned constants so they can be tested and diffed over time.
"""
from __future__ import annotations

from app.config import get_settings
from app.logging_config import get_logger

log = get_logger("llm")

# Versioned prompt templates -------------------------------------------------
ANSWER_SYSTEM_PROMPT_V1 = (
    "You are GraphIntel, a support and incident intelligence assistant. "
    "Answer ONLY from the provided evidence. Every claim must be grounded in a "
    "citation id from the context. If evidence is insufficient, say so explicitly. "
    "Be concise and operational."
)


class LLMProvider:
    """Base provider. `available` indicates whether real generation is possible."""

    name = "base"
    available = False

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str:
        raise NotImplementedError


class DeterministicLLM(LLMProvider):
    name = "deterministic"
    available = True

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str:
        # The deterministic path never free-generates; the answer service builds
        # templated text directly. This exists so callers have a uniform API.
        return prompt


class AnthropicLLM(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = None
        self.available = False
        try:
            import anthropic  # type: ignore

            self._client = anthropic.Anthropic(api_key=api_key)
            self.available = True
        except Exception as exc:  # pragma: no cover - depends on env
            log.warning("anthropic_unavailable", error=str(exc))

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str:  # pragma: no cover
        if not self._client:
            raise RuntimeError("Anthropic client not available")
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "\n".join(parts).strip()


def get_llm() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        provider = AnthropicLLM(settings.anthropic_api_key, settings.llm_model)
        if provider.available:
            return provider
        log.warning("falling_back_to_deterministic_llm")
    return DeterministicLLM()
