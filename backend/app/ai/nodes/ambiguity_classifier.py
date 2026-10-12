"""
AmbiguityClassifier Node (Task 8.2).
Applies deterministic completeness checks first, with optional fallback for semantic nuance.
"""

from typing import Optional
from app.ai.providers.llm_provider import LLMProvider, get_llm_provider
from app.ai.schemas.structured_output import ClarificationRequest
from app.domain.requirements.completeness import classify_ambiguity_and_completeness
from app.domain.requirements.schemas import RequirementSet


class AmbiguityClassifier:
    """
    Evaluates semantic ambiguity on a parsed RequirementSet.
    Prioritizes deterministic Python rules first.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider("llm_fast")

    def evaluate(self, req_set: RequirementSet) -> ClarificationRequest:
        """
        Evaluate requirement set for completeness and ambiguity.
        """
        # 1. Deterministic rules first (ground truth)
        result = classify_ambiguity_and_completeness(req_set)
        return result

    async def aevaluate(self, req_set: RequirementSet) -> ClarificationRequest:
        """
        Async evaluation.
        """
        return self.evaluate(req_set)
