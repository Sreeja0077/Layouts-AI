# LLM Gateway & Provider Abstraction

## 📌 Purpose & Overview
Unified LLM routing through LiteLLM, Ollama, and testable Mock providers.

## 🏗️ Provider Implementations (`llm_provider.py`)
- **`LLMProvider` (ABC)**: Abstract interface defining `complete` and `acomplete` methods.
- **`LiteLLMProvider`**: Production provider using LiteLLM to route model aliases (`llm_fast`, `llm_reasoning`) to Ollama or configured endpoints via environment variables (`LITELLM_MODEL_FAST`, `OLLAMA_API_BASE`).
- **`MockLLMProvider`**: Deterministic mock provider for offline testing and development. Generates valid `ParsedRequirementOutput` JSON without network access or API keys.
- **Factory (`get_llm_provider`)**: Returns `MockLLMProvider` if `USE_MOCK_LLM=true` or when testing; otherwise returns `LiteLLMProvider`.
