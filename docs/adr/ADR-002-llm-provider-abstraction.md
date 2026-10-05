# ADR-002: LLM Provider Abstraction

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

The system requires LLM capabilities for semantic extraction, decision detection, contradiction analysis, and Ask-the-Meeting queries. No specific LLM provider should be a hard dependency.

## Decision

All LLM calls go through an `LLMAdapter` abstract interface:
```python
class LLMAdapter(ABC):
    async def complete(self, prompt: str, **kwargs) -> str: ...
    async def extract_structured(self, prompt: str, schema: type) -> BaseModel: ...
```

Implementations: `OpenAIAdapter`, `AnthropicAdapter`, `OllamaAdapter`, `StubLLMAdapter`  
Selected via `LLM_PROVIDER` env var.

`StubLLMAdapter` returns deterministic realistic mock data — enables full system dev without any API keys.

## Consequences

- Switching LLM providers requires only changing `LLM_PROVIDER` in `.env`
- No OpenAI-specific SDK calls appear outside `openai_adapter.py`
- Cost tracking uses adapter-specific cost estimates per token
