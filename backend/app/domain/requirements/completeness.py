"""
Deterministic Completeness & Ambiguity Evaluation Engine (Task 8.2).
Evaluates whether a RequirementSet has sufficient semantic clarity to proceed
or whether clarification questions must be asked to the user.
"""

import uuid
from typing import List, Tuple
from app.ai.schemas.structured_output import ClarificationQuestion, ClarificationRequest
from app.domain.requirements.schemas import RequirementSet, RequirementStatus


ROOM_SPACE_TYPES = {
    "CONFERENCE_ROOM",
    "MEETING_ROOM",
    "BOARDROOM",
    "TRAINING_ROOM",
    "HUDDLE_ROOM",
    "WAR_ROOM",
}

GENERIC_DESK_TYPES = {
    "DESK",
    "DESKS",
    "WORKSTATION",
    "WORKSTATIONS",
    "PROFESSIONAL_DESK",
    "EXECUTIVE_DESK",
}


def evaluate_requirement_completeness(
    req_set: RequirementSet,
) -> Tuple[bool, List[ClarificationQuestion], str]:
    """
    Deterministic rule-based completeness checklist.
    Returns: (is_complete, clarification_questions, reasoning)
    """
    questions: List[ClarificationQuestion] = []
    reasons: List[str] = []

    # 1. Empty Check
    if not req_set.items and not req_set.target_density_seats:
        q = ClarificationQuestion(
            question_id=f"q_{uuid.uuid4().hex[:8]}",
            slot="general_requirement",
            question_text="Could you specify what kind of workspace or room you would like to create?",
            suggested_options=["Office Workstations", "Meeting Room", "Conference Room", "Manager Cabin"],
            default_fallback_value=None,
        )
        questions.append(q)
        return False, questions, "No requirement items or room specification provided."

    # 2. Check each requirement item
    for item in req_set.items:
        sem_type = (item.semantic_type or "").upper()
        raw_phrase_lower = item.raw_phrase.lower()

        # Rule 2A: Room/Space Type missing Capacity
        if sem_type in ROOM_SPACE_TYPES:
            # Check if seat capacity is defined either on target_density_seats or quantity
            has_capacity = bool(
                req_set.target_density_seats
                or (item.quantity > 1 and "seater" in raw_phrase_lower)
            )
            if not has_capacity:
                slot_name = f"capacity_{sem_type.lower()}"
                display_name = sem_type.replace("_", " ").title()
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    question_text=f"How many seats are needed for the {display_name}?",
                    suggested_options=["6", "8", "10", "12", "16"],
                    default_fallback_value="8" if sem_type == "MEETING_ROOM" else "10",
                )
                questions.append(q)
                reasons.append(f"{display_name} requires a seating capacity.")

        # Rule 2B: Desks or Workstations with Missing/Zero Quantity
        if sem_type in GENERIC_DESK_TYPES:
            if item.quantity <= 0 or ("desks" in raw_phrase_lower and not any(ch.isdigit() for ch in raw_phrase_lower) and "a desk" not in raw_phrase_lower and "one desk" not in raw_phrase_lower):
                slot_name = f"quantity_{sem_type.lower()}"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    question_text="How many desks would you like to place?",
                    suggested_options=["4", "6", "8", "12"],
                    default_fallback_value="6",
                )
                questions.append(q)
                reasons.append("Desk requirement requires a specific quantity.")

        # Rule 2C: Highly Ambiguous Item (e.g., 'table' without context)
        if sem_type in ("TABLE_GENERIC", "TABLE") or "table" in raw_phrase_lower and sem_type not in ROOM_SPACE_TYPES:
            if not any(k in raw_phrase_lower for k in ["meeting", "conference", "coffee", "desk", "dining"]):
                slot_name = "table_type"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    question_text="What type of table would you like to place?",
                    suggested_options=["Meeting Table", "Coffee Table", "Workstation Table"],
                    default_fallback_value=None,
                )
                questions.append(q)
                reasons.append("Ambiguous table type specified.")

        # Rule 2D: Ambiguous Room ('10 seater room' without room type)
        if sem_type in ("ROOM", "UNKNOWN_ROOM") or ("room" in raw_phrase_lower and sem_type not in ROOM_SPACE_TYPES and sem_type != "MANAGER_CABIN"):
            if not any(k in raw_phrase_lower for k in ["conference", "meeting", "training", "break", "server", "manager"]):
                slot_name = "room_type"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    question_text="What type of room should this be?",
                    suggested_options=["Meeting Room", "Conference Room", "Training Room"],
                    default_fallback_value="Meeting Room",
                )
                questions.append(q)
                reasons.append("Room type is unspecified.")

    is_complete = len(questions) == 0
    reasoning_summary = "; ".join(reasons) if reasons else "Requirement is semantically complete."
    return is_complete, questions, reasoning_summary


def classify_ambiguity_and_completeness(
    req_set: RequirementSet,
) -> ClarificationRequest:
    """
    Wraps deterministic completeness evaluation into a ClarificationRequest structure.
    """
    is_complete, questions, reasoning = evaluate_requirement_completeness(req_set)
    return ClarificationRequest(
        needs_clarification=not is_complete,
        questions=questions,
        reasoning=reasoning,
    )
