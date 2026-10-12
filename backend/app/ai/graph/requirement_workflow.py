"""
LangGraph Requirement Understanding & Clarification Workflow (Task 8.4).
Supports state persistence, pause on clarification required, and resume with user answers.
"""

import logging
import os
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
    target_item_id: Optional[str] = None,
) -> RequirementSet:
    """
    Non-destructively merges a user clarification answer into an existing RequirementSet.
    Preserves all previously valid semantic information and targets specific items when specified.
    """
    answer_clean = answer.strip()
    slot = (question_slot or "").lower()

    # Find the specific target item if target_item_id was passed
    target_item: Optional[RequirementItem] = None
    if target_item_id:
        for item in req_set.items:
            if item.id == target_item_id:
                target_item = item
                break

    # 1. Desk Type answer (slot='desk_type')
    if slot == "desk_type" or ("desk" in slot and "type" in slot):
        norm_type = answer_clean.upper().replace(" ", "_").replace("-", "_")
        if not norm_type.endswith("_DESK") and "DESK" not in norm_type:
            norm_type = f"{norm_type}_DESK"
        if target_item:
            target_item.semantic_type = norm_type
        else:
            # Fallback to first generic desk item
            for item in req_set.items:
                if item.semantic_type in ("DESK_GENERIC", "DESK", "DESKS") or ("DESK" in (item.semantic_type or "")):
                    item.semantic_type = norm_type
                    break
        req_set.notes = f"{req_set.notes or ''} [Clarified desk type: {norm_type}]"

    # 2. Chair Type answer (slot='chair_type')
    elif slot == "chair_type" or ("chair" in slot and "type" in slot):
        norm_type = answer_clean.upper().replace(" ", "_").replace("-", "_")
        if not norm_type.endswith("_CHAIR") and "CHAIR" not in norm_type:
            norm_type = f"{norm_type}_CHAIR"
        if target_item:
            target_item.semantic_type = norm_type
        else:
            for item in req_set.items:
                if item.semantic_type in ("CHAIR_GENERIC", "CHAIR", "CHAIRS") or ("CHAIR" in (item.semantic_type or "")):
                    item.semantic_type = norm_type
                    break
        req_set.notes = f"{req_set.notes or ''} [Clarified chair type: {norm_type}]"

    # 3. Table Type answer (slot='table_type')
    elif slot == "table_type" or ("table" in slot and "type" in slot):
        norm_type = answer_clean.upper().replace(" ", "_").replace("-", "_")
        if not norm_type.endswith("_TABLE") and "TABLE" not in norm_type:
            norm_type = f"{norm_type}_TABLE"
        if target_item:
            target_item.semantic_type = norm_type
        else:
            for item in req_set.items:
                if item.semantic_type in ("TABLE_GENERIC", "TABLE", "TABLES") or ("TABLE" in (item.semantic_type or "")):
                    item.semantic_type = norm_type
                    break
        req_set.notes = f"{req_set.notes or ''} [Clarified table type: {norm_type}]"

    # 4. Capacity answer (e.g. slot='capacity_conference_room')
    elif "capacity" in slot or "seat" in slot:
        val = _extract_first_int(answer_clean)
        if val is not None:
            req_set.target_density_seats = val
            if target_item and "seater" in target_item.raw_phrase.lower():
                target_item.quantity = val
            req_set.notes = f"{req_set.notes or ''} [Clarified capacity: {val}]"

    # 5. Room Type answer (e.g. slot='room_type')
    elif "room_type" in slot:
        norm_type = answer_clean.upper().replace(" ", "_").replace("-", "_")
        if target_item:
            target_item.semantic_type = norm_type
        else:
            for item in req_set.items:
                item.semantic_type = norm_type
        req_set.notes = f"{req_set.notes or ''} [Clarified room type: {norm_type}]"

    # 6. Quantity answer (e.g. slot='quantity_desk', 'quantity_chair', 'quantity')
    elif "quantity" in slot:
        val = _extract_first_int(answer_clean)
        if val is not None:
            if target_item:
                target_item.quantity = val
            else:
                found = False
                for item in req_set.items:
                    if item.quantity <= 0 and item.semantic_type and item.semantic_type.lower() in slot:
                        item.quantity = val
                        found = True
                        break
                if not found:
                    for item in req_set.items:
                        if item.quantity <= 0:
                            item.quantity = val
                            break
            req_set.notes = f"{req_set.notes or ''} [Clarified quantity: {val}]"

    # General fallback
    else:
        num = _extract_first_int(answer_clean)
        if num is not None:
            if target_item:
                target_item.quantity = num
            elif not req_set.target_density_seats:
                req_set.target_density_seats = num
            else:
                for item in req_set.items:
                    if item.quantity <= 0:
                        item.quantity = num
                        break
        else:
            norm_type = answer_clean.upper().replace(" ", "_")
            if target_item:
                target_item.semantic_type = norm_type
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
        """
        Evaluate completeness and apply user clarification answers if resuming.
        Locates the exact pending question by question_id when supplied by frontend.
        """
        req_dict = state["requirement_set"]
        req_set = RequirementSet.model_validate(req_dict)

        # Merge answer if workflow was resumed with clarification response
        user_answer = state.get("user_answer")
        if user_answer:
            slot_name = None
            target_item_id = None
            answered_qid = state.get("answered_question_id")
            pending_questions = state.get("questions") or []

            # 1. Match exact question by question_id if supplied
            if answered_qid and pending_questions:
                for q in pending_questions:
                    if q.get("question_id") == answered_qid:
                        slot_name = q.get("slot")
                        target_item_id = q.get("item_id")
                        break

            # 2. If question_id didn't match or wasn't provided, fallback to first pending question's slot & item_id
            if not slot_name and pending_questions:
                slot_name = pending_questions[0].get("slot")
                target_item_id = pending_questions[0].get("item_id")

            req_set = merge_clarification_answer(
                req_set=req_set,
                answer=user_answer,
                question_slot=slot_name,
                target_item_id=target_item_id,
            )

        is_complete, questions, reasoning = evaluate_requirement_completeness(req_set)

        if not is_complete:
            req_set.status = RequirementStatus.CLARIFICATION_REQUIRED
            return {
                "requirement_set": req_set.model_dump(),
                "needs_clarification": True,
                "questions": [q.model_dump() for q in questions],
                "reasoning": reasoning,
                "user_answer": None,
                "answered_question_id": None,
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
                "answered_question_id": None,
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

    memory = checkpointer if checkpointer is not None else get_checkpointer()
    compiled_app = builder.compile(checkpointer=memory)
    return compiled_app


# Checkpointer management
_GLOBAL_CHECKPOINTER: Optional[Any] = None
_GLOBAL_REQUIREMENT_WORKFLOW = None


def get_checkpointer():
    """
    Returns the configured checkpointer.
    Controlled by CHECKPOINT_BACKEND=memory|postgres (default: memory).
    For memory: returns MemorySaver().
    For postgres: returns PostgresSaver initialized with connection pool,
    with automatic table migration setup.
    """
    global _GLOBAL_CHECKPOINTER
    if _GLOBAL_CHECKPOINTER is not None:
        return _GLOBAL_CHECKPOINTER

    backend_type = os.getenv("CHECKPOINT_BACKEND", "memory").lower()
    if backend_type == "postgres":
        try:
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver

            raw_db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres_secure_password@localhost:5432/layouts_ai",
            )
            pg_conn_str = raw_db_url.replace("postgresql+psycopg2://", "postgresql://")
            pool = ConnectionPool(
                pg_conn_str,
                max_size=10,
                open=False,
                kwargs={"autocommit": True, "connect_timeout": 1},
            )
            pool.open(wait=True, timeout=1.0)
            saver = PostgresSaver(pool)
            saver.setup()
            _GLOBAL_CHECKPOINTER = saver
            logger.info("Initialized durable PostgreSQL checkpointer for LangGraph.")
            return _GLOBAL_CHECKPOINTER
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
            raise RuntimeError(f"PostgreSQL checkpointer initialization failed: {e}") from e

    _GLOBAL_CHECKPOINTER = MemorySaver()
    logger.info("Initialized in-memory checkpointer for LangGraph.")
    return _GLOBAL_CHECKPOINTER


def set_global_checkpointer(checkpointer: Optional[Any]) -> None:
    """Override checkpointer instance for testing."""
    global _GLOBAL_CHECKPOINTER, _GLOBAL_REQUIREMENT_WORKFLOW
    _GLOBAL_CHECKPOINTER = checkpointer
    _GLOBAL_REQUIREMENT_WORKFLOW = None


def get_requirement_workflow(
    provider: Optional[LLMProvider] = None,
    checkpointer: Optional[Any] = None,
):
    """Get compiled LangGraph requirement workflow."""
    global _GLOBAL_REQUIREMENT_WORKFLOW
    if _GLOBAL_REQUIREMENT_WORKFLOW is None or provider is not None or checkpointer is not None:
        active_checkpointer = checkpointer if checkpointer is not None else get_checkpointer()
        _GLOBAL_REQUIREMENT_WORKFLOW = build_requirement_workflow(
            provider=provider, checkpointer=active_checkpointer
        )
    return _GLOBAL_REQUIREMENT_WORKFLOW
