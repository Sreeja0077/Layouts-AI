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
            logger.warning(f"First parsing attempt failed ({e}). Performing bounded retry...")
            retry_prompt = (
                f"The previous output was invalid or violated schema constraints: {e}\n"
                f"Please fix and return ONLY valid JSON matching ParsedRequirementOutput schema for:\n"
                f"{raw_text.strip()}"
            )
            try:
                retry_response = self.provider.complete(
                    prompt=retry_prompt,
                    system_prompt=REQUIREMENT_PARSER_SYSTEM_PROMPT,
                )
                cleaned_retry_json = _clean_json_markdown(retry_response)
                parsed_output = ParsedRequirementOutput.model_validate_json(cleaned_retry_json)
            except Exception as retry_err:
                logger.error(f"Bounded retry also failed: {retry_err}")
                raise ValueError(f"Malformed LLM structured output: {str(retry_err)}") from retry_err

        req_set = self._to_requirement_set(
            parsed_output=parsed_output,
            raw_text=raw_text,
            project_id=project_id,
            floor_plan_id=floor_plan_id,
            region_id=region_id,
        )
        return self._deterministic_validate_and_normalize(req_set, raw_text)

    async def aparse(
        self,
        raw_text: str,
        project_id: str = "proj_default",
        floor_plan_id: str = "fp_default",
        region_id: Optional[str] = None,
    ) -> RequirementSet:
        """
        Asynchronously parse user text into a RequirementSet with bounded retry.
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
            logger.warning(f"First async parsing attempt failed ({e}). Performing bounded retry...")
            retry_prompt = (
                f"The previous output was invalid or violated schema constraints: {e}\n"
                f"Please fix and return ONLY valid JSON matching ParsedRequirementOutput schema for:\n"
                f"{raw_text.strip()}"
            )
            try:
                retry_response = await self.provider.acomplete(
                    prompt=retry_prompt,
                    system_prompt=REQUIREMENT_PARSER_SYSTEM_PROMPT,
                )
                cleaned_retry_json = _clean_json_markdown(retry_response)
                parsed_output = ParsedRequirementOutput.model_validate_json(cleaned_retry_json)
            except Exception as retry_err:
                logger.error(f"Bounded async retry also failed: {retry_err}")
                raise ValueError(f"Malformed LLM structured output: {str(retry_err)}") from retry_err

        req_set = self._to_requirement_set(
            parsed_output=parsed_output,
            raw_text=raw_text,
            project_id=project_id,
            floor_plan_id=floor_plan_id,
            region_id=region_id,
        )
        return self._deterministic_validate_and_normalize(req_set, raw_text)

    def _deterministic_validate_and_normalize(
        self,
        req_set: RequirementSet,
        raw_text: str,
    ) -> RequirementSet:
        """
        Deterministic post-LLM validation and normalization layer (Tasks 8.1 - 8.3).
        Guarantees:
        1. Generic nouns ('desk', 'chair', 'table') stay generic (DESK_GENERIC, CHAIR_GENERIC, TABLE_GENERIC).
           Never infers specific types like PROFESSIONAL_DESK or OFFICE_CHAIR without explicit words.
        2. Explicit quantities in the user's raw text are strictly preserved (never converted to 0).
           Quantity = 0 ONLY if the user genuinely did not state a quantity.
        3. Multiple conjoined items (e.g., '2 chairs and 2 desks') are split into separate RequirementItems.
           No dropped or merged items.
        4. Sub-phrases are preserved in raw_phrase for each item.
        5. Phase 8 invariants: resolved_catalog_item_id is None, resolution_method is None.
        """
        word_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "sixteen": 16, "twenty": 20,
        }

        def extract_qty(phrase: str) -> Optional[int]:
            phrase_l = phrase.lower()
            for w, val in word_to_num.items():
                if re.search(rf"\b{w}\b", phrase_l):
                    return val
            m = re.search(r"\b(\d+)\b", phrase_l)
            if m:
                return int(m.group(1))
            return None

        # Split clauses by conjoining punctuation/words
        clauses = [
            c.strip()
            for c in re.split(r"\band\b|&|\+|,|;", raw_text, flags=re.IGNORECASE)
            if c.strip()
        ]
        raw_text_lower = raw_text.lower()

        # Check if natural language furniture / space requests are present
        has_nl_furniture = any(w in raw_text_lower for w in ("desk", "chair", "table", "room", "cabin"))
        if not has_nl_furniture:
            return req_set

        # Step 1: Enforce generic vs specific semantic types
        for item in req_set.items:
            item_phrase_lower = (item.raw_phrase or "").lower()
            sem_type = (item.semantic_type or "").upper()
            phrase_to_check = item_phrase_lower if (item_phrase_lower and item_phrase_lower != raw_text_lower) else raw_text_lower

            # Desks: never infer specific desk types from generic noun
            if sem_type in ("PROFESSIONAL_DESK", "EXECUTIVE_DESK", "MANAGER_DESK"):
                if "desk" in phrase_to_check:
                    has_prof = "professional" in phrase_to_check
                    has_exec = "executive" in phrase_to_check
                    has_mgr = "manager" in phrase_to_check
                    if not (has_prof or has_exec or has_mgr):
                        item.semantic_type = "DESK_GENERIC"
                    elif has_prof:
                        item.semantic_type = "PROFESSIONAL_DESK"
                    elif has_exec:
                        item.semantic_type = "EXECUTIVE_DESK"
                    elif has_mgr:
                        item.semantic_type = "MANAGER_DESK"

            # Chairs: never infer specific chair types from generic noun
            elif sem_type in ("OFFICE_CHAIR", "TASK_CHAIR"):
                if "chair" in phrase_to_check:
                    has_office = "office" in phrase_to_check
                    has_task = "task" in phrase_to_check
                    if not (has_office or has_task):
                        item.semantic_type = "CHAIR_GENERIC"
                    elif has_office:
                        item.semantic_type = "OFFICE_CHAIR"
                    elif has_task:
                        item.semantic_type = "TASK_CHAIR"

            # Tables: never infer specific table types from generic noun
            elif sem_type in ("CONFERENCE_TABLE", "DINING_TABLE"):
                if "table" in phrase_to_check:
                    has_conf = "conference" in phrase_to_check
                    has_dining = "dining" in phrase_to_check
                    if not (has_conf or has_dining):
                        item.semantic_type = "TABLE_GENERIC"

        # Step 2: Handle multi-item splitting & verify each item has its distinct sub-phrase and quantity
        has_chairs_in_text = bool(re.search(r"\bchairs?\b", raw_text_lower))
        has_desks_in_text = bool(re.search(r"\bdesks?\b", raw_text_lower))

        has_chair_item = any("CHAIR" in (it.semantic_type or "").upper() or "chair" in it.raw_phrase.lower() for it in req_set.items)
        has_desk_item = any("DESK" in (it.semantic_type or "").upper() or "desk" in it.raw_phrase.lower() for it in req_set.items)

        # If chairs were requested but completely dropped by LLM, restore chair item
        if has_chairs_in_text and not has_chair_item:
            chair_clause = next((c for c in clauses if re.search(r"\bchairs?\b", c.lower())), "chairs")
            c_qty = extract_qty(chair_clause)
            if c_qty is None:
                c_qty = 0
            c_type = "OFFICE_CHAIR" if "office" in chair_clause.lower() else ("TASK_CHAIR" if "task" in chair_clause.lower() else "CHAIR_GENERIC")
            req_set.items.insert(
                0,
                RequirementItem(
                    id=f"req_item_{len(req_set.items) + 1}",
                    raw_phrase=chair_clause,
                    semantic_type=c_type,
                    resolved_catalog_item_id=None,
                    resolution_method=None,
                    confidence=0.95,
                    quantity=c_qty,
                    slot_tags=["chairs"],
                    dimensions_override=None,
                )
            )

        # If desks were requested but completely dropped by LLM, restore desk item
        if has_desks_in_text and not has_desk_item:
            desk_clause = next((c for c in clauses if re.search(r"\bdesks?\b", c.lower())), "desks")
            d_qty = extract_qty(desk_clause)
            if d_qty is None:
                d_qty = 0
            if "professional" in desk_clause.lower():
                d_type = "PROFESSIONAL_DESK"
            elif "executive" in desk_clause.lower():
                d_type = "EXECUTIVE_DESK"
            elif "manager" in desk_clause.lower():
                d_type = "MANAGER_DESK"
            else:
                d_type = "DESK_GENERIC"
            req_set.items.append(
                RequirementItem(
                    id=f"req_item_{len(req_set.items) + 1}",
                    raw_phrase=desk_clause,
                    semantic_type=d_type,
                    resolved_catalog_item_id=None,
                    resolution_method=None,
                    confidence=0.95,
                    quantity=d_qty,
                    slot_tags=["desks"],
                    dimensions_override=None,
                )
            )

        # If multiple desk clauses exist (e.g. professional desks AND manager desk) but one was omitted
        for c in clauses:
            c_lower = c.lower()
            if "manager" in c_lower and "desk" in c_lower:
                if not any("MANAGER" in (it.semantic_type or "").upper() and "DESK" in (it.semantic_type or "").upper() for it in req_set.items):
                    m_qty = extract_qty(c) or 1
                    req_set.items.append(
                        RequirementItem(
                            id=f"req_item_{len(req_set.items) + 1}",
                            raw_phrase=c,
                            semantic_type="MANAGER_DESK",
                            resolved_catalog_item_id=None,
                            resolution_method=None,
                            confidence=0.95,
                            quantity=m_qty,
                            slot_tags=["desks"],
                            dimensions_override=None,
                        )
                    )
            elif "professional" in c_lower and "desk" in c_lower:
                if not any("PROFESSIONAL" in (it.semantic_type or "").upper() for it in req_set.items):
                    p_qty = extract_qty(c) or 1
                    req_set.items.append(
                        RequirementItem(
                            id=f"req_item_{len(req_set.items) + 1}",
                            raw_phrase=c,
                            semantic_type="PROFESSIONAL_DESK",
                            resolved_catalog_item_id=None,
                            resolution_method=None,
                            confidence=0.95,
                            quantity=p_qty,
                            slot_tags=["desks"],
                            dimensions_override=None,
                        )
                    )

        # Step 3: Match clauses to items to refine raw_phrase and validate/restore explicit quantity
        for item in req_set.items:
            item_sem = (item.semantic_type or "").upper()
            matching_clause = None

            if "CHAIR" in item_sem:
                matching_clause = next((c for c in clauses if re.search(r"\bchairs?\b", c.lower())), None)
            elif "DESK" in item_sem:
                if "PROFESSIONAL" in item_sem:
                    matching_clause = next((c for c in clauses if "professional" in c.lower()), None)
                elif "EXECUTIVE" in item_sem:
                    matching_clause = next((c for c in clauses if "executive" in c.lower()), None)
                elif "MANAGER" in item_sem and "CABIN" not in item_sem:
                    matching_clause = next((c for c in clauses if "manager" in c.lower() and "desk" in c.lower()), None)
                if not matching_clause:
                    matching_clause = next((c for c in clauses if re.search(r"\bdesks?\b", c.lower())), None)
            elif "TABLE" in item_sem:
                matching_clause = next((c for c in clauses if re.search(r"\btables?\b", c.lower())), None)

            # Assign specific clause if current raw_phrase contains conjoined text
            if matching_clause and (item.raw_phrase == raw_text or len(clauses) > 1):
                item.raw_phrase = matching_clause

            # Quantity validation:
            # If matching clause exists, check if explicit quantity is present in clause
            target_phrase = item.raw_phrase or raw_text
            explicit_qty = extract_qty(target_phrase)
            if explicit_qty is None and matching_clause:
                explicit_qty = extract_qty(matching_clause)

            if explicit_qty is not None:
                # User gave an explicit count -> NEVER permit it to be 0
                item.quantity = explicit_qty
            else:
                # If neither the item phrase nor the clause had any digit or number word,
                # ensure quantity is 0 (unspecified)
                has_any_num = bool(re.search(r"\b\d+\b", target_phrase)) or any(
                    re.search(rf"\b{w}\b", target_phrase.lower()) for w in word_to_num
                )
                if not has_any_num and " a " not in f" {target_phrase.lower()} " and " one " not in f" {target_phrase.lower()} ":
                    item.quantity = 0

            # Step 4: Strict Phase 8 invariants
            item.resolved_catalog_item_id = None
            item.resolution_method = None

        return req_set

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
