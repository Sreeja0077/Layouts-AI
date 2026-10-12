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
        self.api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

    def _resolve_model_name(self, alias: str) -> str:
        if alias == "llm_fast":
            return os.getenv("LITELLM_MODEL_FAST", "ollama/llama3.2:3b")
        elif alias == "llm_reasoning":
            return os.getenv("LITELLM_MODEL_REASONING", "ollama/llama3.1:8b")
        return os.getenv("LITELLM_MODEL", alias)

    def _build_messages(self, prompt: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        try:
            import litellm
        except ImportError:
            raise RuntimeError("litellm is not installed. Please install litellm or use MockLLMProvider.")

        messages = self._build_messages(prompt, system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
        }
        if "ollama" in self.model_name and self.api_base:
            kwargs["api_base"] = self.api_base

        if response_model is not None:
            kwargs["response_format"] = response_model

        logger.info(f"Invoking LiteLLMProvider with model={self.model_name}, alias={self.model_alias}")
        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return content

    async def acomplete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        try:
            import litellm
        except ImportError:
            raise RuntimeError("litellm is not installed. Please install litellm or use MockLLMProvider.")

        messages = self._build_messages(prompt, system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
        }
        if "ollama" in self.model_name and self.api_base:
            kwargs["api_base"] = self.api_base

        if response_model is not None:
            kwargs["response_format"] = response_model

        logger.info(f"Invoking LiteLLMProvider async with model={self.model_name}, alias={self.model_alias}")
        response = await litellm.acompletion(**kwargs)
        content = response.choices[0].message.content
        return content


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
    Defaults to MockLLMProvider if USE_MOCK_LLM=true or force_mock=True.
    """
    global _ACTIVE_PROVIDER
    if force_mock or os.getenv("USE_MOCK_LLM", "true").lower() in ("true", "1", "yes"):
        return MockLLMProvider()

    if _ACTIVE_PROVIDER is None:
        try:
            _ACTIVE_PROVIDER = LiteLLMProvider(model_alias=alias)
        except Exception as e:
            logger.warning(f"Could not initialize LiteLLMProvider ({e}). Falling back to MockLLMProvider.")
            _ACTIVE_PROVIDER = MockLLMProvider()

    return _ACTIVE_PROVIDER


def set_active_llm_provider(provider: Optional[LLMProvider]) -> None:
    """Override active provider for testing or specific workflows."""
    global _ACTIVE_PROVIDER
    _ACTIVE_PROVIDER = provider
