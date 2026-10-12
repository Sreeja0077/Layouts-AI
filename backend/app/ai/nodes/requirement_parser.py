"""
RequirementParser AI Node (Task 8.1).
Translates raw natural-language user requests into structured semantic RequirementSet domain entities.
Adheres strictly to the architectural boundary:
Semantic intent parsing only. Zero physical catalog or Revit family resolution.
"""

import json
import logging
import re
import uuid
from typing import Optional
from pydantic import ValidationError

from app.ai.prompts.requirement_prompts import REQUIREMENT_PARSER_SYSTEM_PROMPT
from app.ai.providers.llm_provider import LLMProvider, get_llm_provider
from app.ai.schemas.structured_output import ParsedRequirementOutput
from app.domain.requirements.schemas import (
    RequirementItem,
    RequirementSet,
    RequirementStatus,
    SpatialPreference,
)

logger = logging.getLogger("app.ai.nodes.requirement_parser")


def _clean_json_markdown(text: str) -> str:
    """Strip markdown code fence blocks if returned by LLM."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


class RequirementParser:
    """
    Parses unstructured user text into structured ParsedRequirementOutput
    and maps to domain RequirementSet.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider("llm_fast")

    def parse(
        self,
        raw_text: str,
        project_id: str = "proj_default",
        floor_plan_id: str = "fp_default",
        region_id: Optional[str] = None,
    ) -> RequirementSet:
        """
        Synchronously parse user text into a RequirementSet.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Input raw_text cannot be empty")

        logger.info(f"RequirementParser parsing text: '{raw_text[:50]}...'")

        raw_response = self.provider.complete(
            prompt=raw_text.strip(),
            system_prompt=REQUIREMENT_PARSER_SYSTEM_PROMPT,
        )

        cleaned_json = _clean_json_markdown(raw_response)

        try:
            parsed_output = ParsedRequirementOutput.model_validate_json(cleaned_json)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"Failed to validate LLM output against ParsedRequirementOutput: {e}")
            raise ValueError(f"Malformed LLM structured output: {str(e)}")

        return self._to_requirement_set(
            parsed_output=parsed_output,
            raw_text=raw_text,
            project_id=project_id,
            floor_plan_id=floor_plan_id,
            region_id=region_id,
        )

    async def aparse(
        self,
        raw_text: str,
        project_id: str = "proj_default",
        floor_plan_id: str = "fp_default",
        region_id: Optional[str] = None,
    ) -> RequirementSet:
        """
        Asynchronously parse user text into a RequirementSet.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Input raw_text cannot be empty")

        logger.info(f"RequirementParser aparse text: '{raw_text[:50]}...'")

        raw_response = await self.provider.acomplete(
            prompt=raw_text.strip(),
            system_prompt=REQUIREMENT_PARSER_SYSTEM_PROMPT,
        )

        cleaned_json = _clean_json_markdown(raw_response)

        try:
            parsed_output = ParsedRequirementOutput.model_validate_json(cleaned_json)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"Failed to validate LLM output against ParsedRequirementOutput: {e}")
            raise ValueError(f"Malformed LLM structured output: {str(e)}")

        return self._to_requirement_set(
            parsed_output=parsed_output,
            raw_text=raw_text,
            project_id=project_id,
            floor_plan_id=floor_plan_id,
            region_id=region_id,
        )

    def _to_requirement_set(
        self,
        parsed_output: ParsedRequirementOutput,
        raw_text: str,
        project_id: str,
        floor_plan_id: str,
        region_id: Optional[str],
    ) -> RequirementSet:
        """
        Convert ParsedRequirementOutput to domain RequirementSet.
        Enforces Phase 8 invariants:
        - resolved_catalog_item_id is None
        - resolution_method is None
        - preserved raw_phrase and semantic_type
        """
        domain_items = []
        for idx, item in enumerate(parsed_output.items):
            item_id = item.id if item.id and item.id != "string" else f"req_item_{idx + 1}"
            domain_items.append(
                RequirementItem(
                    id=item_id,
                    raw_phrase=item.raw_phrase or raw_text,
                    semantic_type=item.semantic_type,
                    resolved_catalog_item_id=None,  # Intentionally unresolved in Phase 8
                    resolution_method=None,  # Intentionally unresolved in Phase 8
                    confidence=item.confidence,
                    quantity=max(item.quantity, 0),
                    slot_tags=item.slot_tags,
                    dimensions_override=item.dimensions_override,
                )
            )

        domain_preferences = []
        for pref in parsed_output.preferences:
            domain_preferences.append(
                SpatialPreference(
                    target_zone=pref.target_zone,
                    item_ids_or_tags=pref.item_ids_or_tags,
                    preference_type=pref.preference_type,
                    importance=pref.importance,
                )
            )

        status = (
            RequirementStatus.NORMALIZED
            if parsed_output.confidence_score >= 0.8
            else RequirementStatus.DRAFT
        )

        return RequirementSet(
            id=str(uuid.uuid4()),
            project_id=project_id,
            floor_plan_id=floor_plan_id,
            room_id=region_id,
            status=status,
            items=domain_items,
            preferences=domain_preferences,
            target_density_seats=parsed_output.target_density_seats,
            notes=f"Summary: {parsed_output.summary} | Original: {raw_text}",
        )
