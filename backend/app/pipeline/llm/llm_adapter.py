"""
pipeline/llm/llm_adapter.py — Abstract LLM provider interface.

ALL LLM calls in the system go through this interface.
Never import openai, anthropic, or any provider SDK outside of their adapter files.

See ADR-002 for rationale.
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMAdapter(ABC):
    """
    Abstract LLM provider interface.

    Implementations: OpenAIAdapter, AnthropicAdapter, OllamaAdapter, StubLLMAdapter
    Selected via LLM_PROVIDER env var in config.py.
    """

    @abstractmethod
    async def complete(self, prompt: str, system: str = "", **kwargs: Any) -> str:
        """
        Generate a text completion.

        Args:
            prompt: The user prompt
            system: Optional system instruction
        Returns:
            Generated text string
        """

    @abstractmethod
    async def extract_structured(
        self,
        prompt: str,
        schema: type[T],
        system: str = "",
        **kwargs: Any,
    ) -> T:
        """
        Generate a structured output conforming to a Pydantic schema.

        The implementation must use function-calling or JSON mode where available.
        The result must be validated against the schema before returning.

        Args:
            prompt: The extraction prompt
            schema: Pydantic model class for the expected output
            system: Optional system instruction
        Returns:
            Validated Pydantic model instance
        """

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost in USD for a completion of given token counts.
        Used by ProcessingLedger. Return 0.0 for local/free providers.
        """


def get_llm_adapter() -> LLMAdapter:
    """Factory: return the configured LLM adapter."""
    from app.config import settings
    from app.config import LLMProvider

    if settings.llm_provider == LLMProvider.STUB:
        from app.pipeline.llm.stub_llm import StubLLMAdapter
        return StubLLMAdapter()
    elif settings.llm_provider == LLMProvider.OPENAI:
        from app.pipeline.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter()
    elif settings.llm_provider == LLMProvider.ANTHROPIC:
        from app.pipeline.llm.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter()
    elif settings.llm_provider == LLMProvider.OLLAMA:
        from app.pipeline.llm.ollama_adapter import OllamaAdapter
        return OllamaAdapter()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
