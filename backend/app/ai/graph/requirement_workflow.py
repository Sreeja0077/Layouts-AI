"""
LangGraph Requirement Understanding & Clarification Workflow (Task 8.4).
Supports state persistence, pause on clarification required, and resume with user answers.
"""

import logging
import re
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.ai.nodes.requirement_parser import RequirementParser
from app.ai.providers.llm_provider import LLMProvider, get_llm_provider
from app.ai.schemas.structured_output import ClarificationQuestion
from app.domain.requirements.completeness import evaluate_requirement_completeness
from app.domain.requirements.schemas import RequirementItem, RequirementSet, RequirementStatus

logger = logging.getLogger("app.ai.graph.requirement_workflow")


class RequirementWorkflowState(TypedDict, total=False):
    """LangGraph state representation for Requirement Workflow."""
    project_id: str
    floor_plan_id: str
    region_id: Optional[str]
    raw_text: str
    requirement_set: Dict[str, Any]
    needs_clarification: bool
    questions: List[Dict[str, Any]]
    reasoning: str
    user_answer: Optional[str]
    answered_question_id: Optional[str]
    status: str


def _extract_first_int(text: str) -> Optional[int]:
    """Helper to extract integer value from natural language answer like '10' or '10 seats'."""
    text_clean = text.strip().lower()
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twelve": 12, "sixteen": 16, "twenty": 20,
    }
    for word, val in word_map.items():
        if word in text_clean:
            return val
    match = re.search(r"\b(\d+)\b", text_clean)
    if match:
        return int(match.group(1))
    return None


def merge_clarification_answer(
    req_set: RequirementSet,
    answer: str,
    question_slot: Optional[str] = None,
) -> RequirementSet:
    """
    Non-destructively merges a user clarification answer into an existing RequirementSet.
    Preserves all previously valid semantic information.
    """
    answer_clean = answer.strip()
    slot = (question_slot or "").lower()

    # 1. Capacity answer (e.g. slot='capacity_conference_room')
    if "capacity" in slot or "seat" in slot:
        val = _extract_first_int(answer_clean)
        if val is not None:
            req_set.target_density_seats = val
            # Update notes
            req_set.notes = f"{req_set.notes or ''} [Clarified capacity: {val}]"

    # 2. Quantity answer (e.g. slot='quantity_professional_desk')
    elif "quantity" in slot or "desk" in slot:
        val = _extract_first_int(answer_clean)
        if val is not None:
            for item in req_set.items:
                if item.quantity <= 0 or (item.semantic_type and "DESK" in item.semantic_type):
                    item.quantity = val
            req_set.notes = f"{req_set.notes or ''} [Clarified quantity: {val}]"

    # 3. Room Type answer (e.g. slot='room_type')
    elif "room_type" in slot:
        norm_type = answer_clean.upper().replace(" ", "_")
        for item in req_set.items:
            item.semantic_type = norm_type
        req_set.notes = f"{req_set.notes or ''} [Clarified room type: {norm_type}]"

    # 4. Table Type answer (e.g. slot='table_type')
    elif "table_type" in slot:
        norm_type = answer_clean.upper().replace(" ", "_")
        for item in req_set.items:
            item.semantic_type = norm_type
        req_set.notes = f"{req_set.notes or ''} [Clarified table type: {norm_type}]"

    # General fallback
    else:
        num = _extract_first_int(answer_clean)
        if num is not None:
            if not req_set.target_density_seats:
                req_set.target_density_seats = num
            else:
                for item in req_set.items:
                    if item.quantity <= 0:
                        item.quantity = num
        req_set.notes = f"{req_set.notes or ''} [Clarification: {answer_clean}]"

    return req_set


def build_requirement_workflow(
    provider: Optional[LLMProvider] = None,
    checkpointer: Optional[Any] = None,
):
    """
    Constructs the LangGraph Requirement Understanding & Clarification StateGraph.
    Flow:
    START -> parse_node -> evaluate_node -> (branch: complete -> finalize_node / incomplete -> clarification_pause_node)
    """
    llm_provider = provider or get_llm_provider("llm_fast")
    parser = RequirementParser(provider=llm_provider)

    def parse_node(state: RequirementWorkflowState) -> Dict[str, Any]:
        """Parse raw text if requirement_set is not already initialized."""
        if state.get("requirement_set"):
            return {}

        req_set = parser.parse(
            raw_text=state["raw_text"],
            project_id=state.get("project_id", "proj_default"),
            floor_plan_id=state.get("floor_plan_id", "fp_default"),
            region_id=state.get("region_id"),
        )
        return {
            "requirement_set": req_set.model_dump(),
            "status": req_set.status.value,
        }

    def evaluate_node(state: RequirementWorkflowState) -> Dict[str, Any]:
        """Evaluate completeness and apply user clarification answers if resuming."""
        req_dict = state["requirement_set"]
        req_set = RequirementSet.model_validate(req_dict)

        # Merge answer if workflow was resumed with clarification response
        user_answer = state.get("user_answer")
        if user_answer:
            slot_name = None
            if state.get("questions"):
                slot_name = state["questions"][0].get("slot")
            req_set = merge_clarification_answer(req_set, user_answer, slot_name)

        is_complete, questions, reasoning = evaluate_requirement_completeness(req_set)

        if not is_complete:
            req_set.status = RequirementStatus.CLARIFICATION_REQUIRED
            return {
                "requirement_set": req_set.model_dump(),
                "needs_clarification": True,
                "questions": [q.model_dump() for q in questions],
                "reasoning": reasoning,
                "user_answer": None,
                "status": RequirementStatus.CLARIFICATION_REQUIRED.value,
            }
        else:
            req_set.status = RequirementStatus.NORMALIZED
            return {
                "requirement_set": req_set.model_dump(),
                "needs_clarification": False,
                "questions": [],
                "reasoning": reasoning,
                "user_answer": None,
                "status": RequirementStatus.NORMALIZED.value,
            }

    def clarification_pause_node(state: RequirementWorkflowState) -> Dict[str, Any]:
        """Terminal node when clarification is required from user."""
        logger.info(f"Requirement workflow paused. Clarification needed: {state.get('reasoning')}")
        return {"status": RequirementStatus.CLARIFICATION_REQUIRED.value}

    def finalize_node(state: RequirementWorkflowState) -> Dict[str, Any]:
        """Terminal node when requirement is semantically complete and normalized."""
        logger.info("Requirement workflow complete. State normalized.")
        return {"status": RequirementStatus.NORMALIZED.value}

    def route_completeness(state: RequirementWorkflowState) -> str:
        """Conditional routing based on completeness check."""
        if state.get("needs_clarification", False):
            return "clarification_pause"
        return "finalize"

    # Assemble Graph
    builder = StateGraph(RequirementWorkflowState)
    builder.add_node("parse_node", parse_node)
    builder.add_node("evaluate_node", evaluate_node)
    builder.add_node("clarification_pause", clarification_pause_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "parse_node")
    builder.add_edge("parse_node", "evaluate_node")
    builder.add_conditional_edges(
        "evaluate_node",
        route_completeness,
        {
            "clarification_pause": "clarification_pause",
            "finalize": "finalize",
        },
    )
    builder.add_edge("clarification_pause", END)
    builder.add_edge("finalize", END)

    memory = checkpointer if checkpointer is not None else MemorySaver()
    compiled_app = builder.compile(checkpointer=memory)
    return compiled_app


# Global workflow instance with in-memory checkpointer
_GLOBAL_CHECKPOINTER = MemorySaver()
_GLOBAL_REQUIREMENT_WORKFLOW = None


def get_requirement_workflow(provider: Optional[LLMProvider] = None):
    """Get compiled LangGraph requirement workflow."""
    global _GLOBAL_REQUIREMENT_WORKFLOW
    if _GLOBAL_REQUIREMENT_WORKFLOW is None or provider is not None:
        _GLOBAL_REQUIREMENT_WORKFLOW = build_requirement_workflow(
            provider=provider, checkpointer=_GLOBAL_CHECKPOINTER
        )
    return _GLOBAL_REQUIREMENT_WORKFLOW
