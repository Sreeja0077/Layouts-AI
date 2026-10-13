import json
import logging
from typing import Optional
from app.ai.nodes.requirement_parser import _clean_json_markdown
from app.ai.prompts.requirement_prompts import AMBIGUITY_CLASSIFIER_SYSTEM_PROMPT
from app.ai.providers.llm_provider import LLMProvider, get_llm_provider
from app.ai.schemas.structured_output import ClarificationRequest
from app.domain.requirements.completeness import classify_ambiguity_and_completeness
from app.domain.requirements.schemas import RequirementSet

logger = logging.getLogger("app.ai.nodes.ambiguity_classifier")


class AmbiguityClassifier:
    """
    Evaluates semantic ambiguity on a parsed RequirementSet.
    Step 1: Run deterministic completeness checks first (ground truth baseline).
    Step 2: If deterministic checks pass, invoke configured LLM to inspect semantic ambiguity.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider("llm_fast")

    def evaluate(self, req_set: RequirementSet, architectural_context: Optional[dict] = None) -> ClarificationRequest:
        """
        Evaluate requirement set for completeness and ambiguity.
        """
        # Step 1: Deterministic rules first (ground truth)
        det_result = classify_ambiguity_and_completeness(req_set, architectural_context=architectural_context)
        if det_result.needs_clarification:
            return det_result

        # Step 2: Semantic ambiguity check via configured LLM provider
        prompt = f"Evaluate this parsed RequirementSet for semantic ambiguity:\n{req_set.model_dump_json(indent=2)}"
        logger.info("Invoking LLM for semantic ambiguity classification.")
        raw_response = self.provider.complete(
            prompt=prompt,
            system_prompt=AMBIGUITY_CLASSIFIER_SYSTEM_PROMPT,
        )
        cleaned = _clean_json_markdown(raw_response)
        try:
            return ClarificationRequest.model_validate_json(cleaned)
        except Exception as e:
            logger.error(f"Failed to validate LLM output for ambiguity classification: {e}")
            raise ValueError(f"Malformed LLM structured output for ambiguity classification: {e}") from e

    async def aevaluate(self, req_set: RequirementSet, architectural_context: Optional[dict] = None) -> ClarificationRequest:
        """
        Async evaluation.
        """
        # Step 1: Deterministic rules first (ground truth)
        det_result = classify_ambiguity_and_completeness(req_set, architectural_context=architectural_context)
        if det_result.needs_clarification:
            return det_result

        # Step 2: Semantic ambiguity check via configured LLM provider
        prompt = f"Evaluate this parsed RequirementSet for semantic ambiguity:\n{req_set.model_dump_json(indent=2)}"
        logger.info("Invoking LLM async for semantic ambiguity classification.")
        raw_response = await self.provider.acomplete(
            prompt=prompt,
            system_prompt=AMBIGUITY_CLASSIFIER_SYSTEM_PROMPT,
        )
        cleaned = _clean_json_markdown(raw_response)
        try:
            return ClarificationRequest.model_validate_json(cleaned)
        except Exception as e:
            logger.error(f"Failed to validate LLM output for async ambiguity classification: {e}")
            raise ValueError(f"Malformed LLM structured output for ambiguity classification: {e}") from e
