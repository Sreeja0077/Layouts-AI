"""
LLM Provider Abstraction Layer (Task 8.1).
Provides unified routing through LiteLLM, Ollama, and testable Mock providers.
Follows the repository invariant:
Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores spatial truth.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

logger = logging.getLogger("app.ai.providers")


class LLMProvider(ABC):
    """Abstract Base Class for LLM providers."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        """Synchronously complete a prompt, returning raw text or JSON string."""
        pass

    @abstractmethod
    async def acomplete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        """Asynchronously complete a prompt, returning raw text or JSON string."""
        pass


class LiteLLMProvider(LLMProvider):
    """
    Production LLM provider routing via LiteLLM.
    Supports model aliases (llm_fast, llm_reasoning) targeting Ollama, local models, or cloud endpoints.
    """

    def __init__(self, model_alias: str = "llm_fast"):
        self.model_alias = model_alias
        self.model_name = self._resolve_model_name(model_alias)
        self.oma_base_url = os.getenv("OMA_BASE_URL", "https://oma.novelinfra.com")
        self.oma_api_key = os.getenv("OMA_API_KEY")
        self.ollama_api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

    def _resolve_model_name(self, alias: str) -> str:
        if alias in ("llm_fast", "spec"):
            return os.getenv("OMA_MODEL_SPEC", os.getenv("LITELLM_MODEL_FAST", "glm-5.2-cloud"))
        elif alias in ("llm_reasoning", "layout"):
            return os.getenv("OMA_MODEL_LAYOUT", os.getenv("LITELLM_MODEL_REASONING", "glm-5.2-cloud"))
        elif alias == "change":
            return os.getenv("OMA_MODEL_CHANGE", "glm-5.2-cloud")
        elif alias == "explain":
            return os.getenv("OMA_MODEL_EXPLAIN", "glm-5.1-cloud")
        elif alias == "ocr":
            return os.getenv("OMA_MODEL_OCR", "glm-ocr-latest")
        elif alias == "vision":
            return os.getenv("OMA_MODEL_VISION", "glm-5.1-cloud")
        elif alias == "code":
            return os.getenv("OMA_MODEL_CODE", "kimi-k2.7-code-cloud")
        return os.getenv("OMA_MODEL_DEFAULT", os.getenv("LITELLM_MODEL", alias))

    def _build_messages(self, prompt: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_kwargs(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        messages = self._build_messages(prompt, system_prompt)
        resolved_model = self.model_name
        api_base = None
        api_key = None

        if "ollama" in self.model_name.lower():
            api_base = self.ollama_api_base
        elif self.oma_base_url or self.oma_api_key:
            api_base = self.oma_base_url
            api_key = self.oma_api_key or os.getenv("OPENAI_API_KEY")
            if not any(resolved_model.startswith(p) for p in ("openai/", "azure/", "ollama/", "anthropic/")):
                resolved_model = f"openai/{resolved_model}"
        elif os.getenv("OPENAI_API_KEY"):
            api_key = os.getenv("OPENAI_API_KEY")

        kwargs: Dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
        }
        if api_base:
            kwargs["api_base"] = api_base
        if api_key:
            kwargs["api_key"] = api_key
        if response_model is not None:
            kwargs["response_format"] = response_model

        return kwargs

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        try:
            import litellm
        except ImportError:
            raise RuntimeError("Configured LLM provider failed: litellm is not installed.")

        kwargs = self._build_kwargs(prompt, system_prompt, response_model)
        logger.info(f"Invoking LiteLLMProvider with model={kwargs.get('model')}, alias={self.model_alias}")
        try:
            response = litellm.completion(**kwargs)
            content = response.choices[0].message.content
            return content
        except Exception as e:
            logger.error(f"Configured LLM provider call failed: {e}")
            raise RuntimeError(f"Configured LLM provider failed: {e}") from e

    async def acomplete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        try:
            import litellm
        except ImportError:
            raise RuntimeError("Configured LLM provider failed: litellm is not installed.")

        kwargs = self._build_kwargs(prompt, system_prompt, response_model)
        logger.info(f"Invoking LiteLLMProvider async with model={kwargs.get('model')}, alias={self.model_alias}")
        try:
            response = await litellm.acompletion(**kwargs)
            content = response.choices[0].message.content
            return content
        except Exception as e:
            logger.error(f"Configured LLM provider async call failed: {e}")
            raise RuntimeError(f"Configured LLM provider failed: {e}") from e


class MockLLMProvider(LLMProvider):
    """
    Deterministic Mock LLM Provider for offline testing and development.
    Requires no internet connection, no API keys, and no running Ollama instance.
    Produces well-formed JSON conforming to ParsedRequirementOutput.
    """

    def __init__(self, custom_responses: Optional[Dict[str, str]] = None):
        self.custom_responses: Dict[str, str] = custom_responses or {}
        self.invocations: List[Dict[str, Any]] = []

    def register_response(self, text_trigger: str, json_response: str) -> None:
        self.custom_responses[text_trigger.lower()] = json_response

    def _generate_mock_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Check explicit custom response triggers first
        for trigger, response in self.custom_responses.items():
            if trigger in prompt_lower:
                return response

        # Ambiguity classifier evaluation prompt support
        if "semantic ambiguity" in prompt_lower:
            return json.dumps({
                "needs_clarification": False,
                "questions": [],
                "reasoning": "Semantic intent is clear and complete."
            })

        # Deterministic semantic inference based on user phrasing:
        # 1. 10 seater conference room
        if "conference" in prompt_lower:
            seats = 10
            for word in ["10", "ten"]:
                if word in prompt_lower:
                    seats = 10
            for word in ["12", "twelve"]:
                if word in prompt_lower:
                    seats = 12
            for word in ["8", "eight"]:
                if word in prompt_lower:
                    seats = 8
            # If no capacity mentioned:
            has_capacity = any(k in prompt_lower for k in ["10", "ten", "12", "twelve", "8", "eight", "seater", "seats", "people"])
            capacity_val = seats if has_capacity else None

            return json.dumps({
                "summary": f"Create a conference room with capacity {capacity_val if capacity_val else 'unspecified'}.",
                "items": [{
                    "id": "req_item_1",
                    "raw_phrase": prompt.strip(),
                    "semantic_type": "CONFERENCE_ROOM",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": 1,
                    "slot_tags": ["conference_room"],
                    "dimensions_override": None
                }],
                "preferences": [],
                "target_density_seats": capacity_val,
                "confidence_score": 0.95
            })

        # 2. Meeting room
        if "meeting" in prompt_lower:
            has_capacity = any(k in prompt_lower for k in ["8", "eight", "10", "ten", "seater", "seats", "people"])
            seats = 8 if has_capacity else None
            prefs = []
            if "window" in prompt_lower:
                prefs.append({
                    "target_zone": "window",
                    "item_ids_or_tags": ["meeting_room"],
                    "preference_type": "NEAR_WINDOW",
                    "importance": "HIGH"
                })
            return json.dumps({
                "summary": "Create a meeting room.",
                "items": [{
                    "id": "req_item_1",
                    "raw_phrase": prompt.strip(),
                    "semantic_type": "MEETING_ROOM",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": 1,
                    "slot_tags": ["meeting_room"],
                    "dimensions_override": None
                }],
                "preferences": prefs,
                "target_density_seats": seats,
                "confidence_score": 0.95
            })

        # 3. Manager cabin near window
        if "manager" in prompt_lower or "cabin" in prompt_lower:
            prefs = []
            if "window" in prompt_lower:
                prefs.append({
                    "target_zone": "window",
                    "item_ids_or_tags": ["manager_cabin"],
                    "preference_type": "NEAR_WINDOW",
                    "importance": "HIGH"
                })
            return json.dumps({
                "summary": "Place 1 manager cabin.",
                "items": [{
                    "id": "req_item_1",
                    "raw_phrase": prompt.strip(),
                    "semantic_type": "MANAGER_CABIN",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": 1,
                    "slot_tags": ["manager_cabin"],
                    "dimensions_override": None
                }],
                "preferences": prefs,
                "target_density_seats": None,
                "confidence_score": 0.95
            })

        # 4. Professional / executive desks with quantities
        if "desk" in prompt_lower:
            # Check for quantity
            qty = 1
            has_explicit_qty = False
            for num_str, num_val in [("6", 6), ("six", 6), ("4", 4), ("four", 4), ("8", 8), ("eight", 8), ("10", 10), ("ten", 10)]:
                if num_str in prompt_lower:
                    qty = num_val
                    has_explicit_qty = True
                    break

            desk_type = "EXECUTIVE_DESK" if "executive" in prompt_lower else "PROFESSIONAL_DESK"
            prefs = []
            if "window" in prompt_lower:
                prefs.append({
                    "target_zone": "window",
                    "item_ids_or_tags": ["desks"],
                    "preference_type": "NEAR_WINDOW",
                    "importance": "HIGH"
                })
            if "perimeter" in prompt_lower:
                prefs.append({
                    "target_zone": "perimeter",
                    "item_ids_or_tags": ["desks"],
                    "preference_type": "ALONG_PERIMETER",
                    "importance": "HIGH"
                })
            if "entrance" in prompt_lower:
                prefs.append({
                    "target_zone": "entrance",
                    "item_ids_or_tags": ["desks"],
                    "preference_type": "NEAR_ENTRANCE",
                    "importance": "MEDIUM"
                })

            # If user said "put desks here" without quantity:
            if not has_explicit_qty:
                return json.dumps({
                    "summary": f"Place {desk_type.lower()}s (unspecified quantity).",
                    "items": [{
                        "id": "req_item_1",
                        "raw_phrase": prompt.strip(),
                        "semantic_type": desk_type,
                        "resolved_catalog_item_id": None,
                        "resolution_method": None,
                        "confidence": 0.65,
                        "quantity": 0,  # Unspecified quantity indicator
                        "slot_tags": ["desks"],
                        "dimensions_override": None
                    }],
                    "preferences": prefs,
                    "target_density_seats": None,
                    "confidence_score": 0.65
                })

            return json.dumps({
                "summary": f"Place {qty} {desk_type.lower()}s.",
                "items": [{
                    "id": "req_item_1",
                    "raw_phrase": prompt.strip(),
                    "semantic_type": desk_type,
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": qty,
                    "slot_tags": ["desks"],
                    "dimensions_override": None
                }],
                "preferences": prefs,
                "target_density_seats": qty,
                "confidence_score": 0.95
            })

        # 5. Generic ambiguous input
        if "table" in prompt_lower:
            return json.dumps({
                "summary": "Place a table (ambiguous type).",
                "items": [{
                    "id": "req_item_1",
                    "raw_phrase": prompt.strip(),
                    "semantic_type": "TABLE_GENERIC",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.5,
                    "quantity": 1,
                    "slot_tags": ["table"],
                    "dimensions_override": None
                }],
                "preferences": [],
                "target_density_seats": None,
                "confidence_score": 0.5
            })

        # Default fallback:
        return json.dumps({
            "summary": f"Understood requirement: {prompt.strip()}",
            "items": [{
                "id": "req_item_1",
                "raw_phrase": prompt.strip(),
                "semantic_type": "UNKNOWN_ELEMENT",
                "resolved_catalog_item_id": None,
                "resolution_method": None,
                "confidence": 0.4,
                "quantity": 1,
                "slot_tags": [],
                "dimensions_override": None
            }],
            "preferences": [],
            "target_density_seats": None,
            "confidence_score": 0.4
        })

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        self.invocations.append({"prompt": prompt, "system_prompt": system_prompt})
        return self._generate_mock_response(prompt)

    async def acomplete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        self.invocations.append({"prompt": prompt, "system_prompt": system_prompt})
        return self._generate_mock_response(prompt)


# Global default provider factory
_ACTIVE_PROVIDER: Optional[LLMProvider] = None


def get_llm_provider(alias: str = "llm_fast", force_mock: bool = False) -> LLMProvider:
    """
    Get the configured LLMProvider instance.
    Uses MockLLMProvider when USE_MOCK_LLM=true or force_mock=True.
    When USE_MOCK_LLM=false, strictly instantiates LiteLLMProvider and does NOT silently fall back to mock.
    """
    global _ACTIVE_PROVIDER
    if force_mock:
        return MockLLMProvider()

    if _ACTIVE_PROVIDER is not None:
        return _ACTIVE_PROVIDER

    if os.getenv("USE_MOCK_LLM", "true").lower() in ("true", "1", "yes"):
        return MockLLMProvider()

    try:
        _ACTIVE_PROVIDER = LiteLLMProvider(model_alias=alias)
    except Exception as e:
        logger.error(f"Failed to initialize LiteLLMProvider: {e}")
        raise RuntimeError(f"Configured LLM provider failed: {e}") from e

    return _ACTIVE_PROVIDER


def set_active_llm_provider(provider: Optional[LLMProvider]) -> None:
    """Override active provider for testing or specific workflows."""
    global _ACTIVE_PROVIDER
    _ACTIVE_PROVIDER = provider
    try:
        from app.ai.graph import requirement_workflow
        requirement_workflow._GLOBAL_REQUIREMENT_WORKFLOW = None
    except ImportError:
        pass
