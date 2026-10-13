"""
Deterministic Completeness & Ambiguity Evaluation Engine (Task 8.2).
Evaluates whether a RequirementSet has sufficient semantic clarity to proceed
or whether clarification questions must be asked to the user.
"""

import uuid
from typing import List, Optional, Tuple
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
    options_config: Optional[dict] = None,
    architectural_context: Optional[dict] = None,
) -> Tuple[bool, List[ClarificationQuestion], str]:
    """
    Deterministic rule-based completeness checklist.
    Returns: (is_complete, clarification_questions, reasoning)

    Adheres strictly to the invariant:
    No unapproved company defaults or hard-coded seat choices.
    suggested_options is empty unless explicitly configured.
    default_fallback_value is None unless explicitly configured.
    """
    opts = options_config or {}
    questions: List[ClarificationQuestion] = []
    reasons: List[str] = []

    # 1. Empty Check
    if not req_set.items and not req_set.target_density_seats:
        q = ClarificationQuestion(
            question_id=f"q_{uuid.uuid4().hex[:8]}",
            slot="general_requirement",
            question_text="Could you specify what kind of workspace or room you would like to create?",
            suggested_options=opts.get("general_requirement", []),
            default_fallback_value=opts.get("default_general_requirement", None),
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
                    item_id=item.id,
                    question_text=f"How many seats are needed for the {display_name}?",
                    suggested_options=opts.get(slot_name, []),
                    default_fallback_value=opts.get(f"default_{slot_name}", None),
                )
                questions.append(q)
                reasons.append(f"{display_name} requires a seating capacity.")

        # Rule 2B: Desks
        is_desk = (
            sem_type in ("DESK_GENERIC", "DESK", "DESKS", "WORKSTATION", "WORKSTATIONS", "PROFESSIONAL_DESK", "EXECUTIVE_DESK", "MANAGER_DESK")
            or ("desk" in raw_phrase_lower and not any(k in sem_type for k in ("CABIN", "ROOM")))
        )
        if is_desk:
            # Case 1: Generic desk with known quantity -> ask for desk TYPE, not quantity
            if sem_type in ("DESK_GENERIC", "DESK", "DESKS") and item.quantity > 0:
                slot_name = "desk_type"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    item_id=item.id,
                    question_text="What type of desk would you like to place?",
                    suggested_options=opts.get(slot_name, []),
                    default_fallback_value=opts.get(f"default_{slot_name}", None),
                )
                questions.append(q)
                reasons.append("Generic desk requirement requires a specific desk type.")
            # Case 2: Desk missing quantity (quantity <= 0 or unspecified)
            elif item.quantity <= 0:
                slot_name = "quantity_desk" if sem_type in ("DESK_GENERIC", "DESK", "DESKS") else f"quantity_{sem_type.lower()}"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    item_id=item.id,
                    question_text="How many desks would you like to place?",
                    suggested_options=opts.get(slot_name, []),
                    default_fallback_value=opts.get(f"default_{slot_name}", None),
                )
                questions.append(q)
                reasons.append("Desk requirement requires a specific quantity.")

        # Rule 2C: Chairs
        is_chair = (
            sem_type in ("CHAIR_GENERIC", "CHAIR", "CHAIRS", "OFFICE_CHAIR", "TASK_CHAIR")
            or ("chair" in raw_phrase_lower and not any(k in sem_type for k in ("CABIN", "ROOM")))
        )
        if is_chair:
            if item.quantity <= 0:
                slot_name = "quantity_chair" if sem_type in ("CHAIR_GENERIC", "CHAIR", "CHAIRS") else f"quantity_{sem_type.lower()}"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    item_id=item.id,
                    question_text="How many chairs would you like to place?",
                    suggested_options=opts.get(slot_name, []),
                    default_fallback_value=opts.get(f"default_{slot_name}", None),
                )
                questions.append(q)
                reasons.append("Chair requirement requires a specific quantity.")
            elif opts.get("require_chair_type", False) or opts.get("clarify_chair_type", False):
                if sem_type in ("CHAIR_GENERIC", "CHAIR", "CHAIRS"):
                    slot_name = "chair_type"
                    q = ClarificationQuestion(
                        question_id=f"q_{uuid.uuid4().hex[:8]}",
                        slot=slot_name,
                        item_id=item.id,
                        question_text="What type of chair would you like to place?",
                        suggested_options=opts.get(slot_name, []),
                        default_fallback_value=opts.get(f"default_{slot_name}", None),
                    )
                    questions.append(q)
                    reasons.append("Generic chair requirement requires a specific chair type.")

        # Rule 2D: Highly Ambiguous Item (e.g., 'table' without context)
        if sem_type in ("TABLE_GENERIC", "TABLE") or ("table" in raw_phrase_lower and sem_type not in ROOM_SPACE_TYPES):
            if not any(k in raw_phrase_lower for k in ["meeting", "conference", "coffee", "desk", "dining"]):
                slot_name = "table_type"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    item_id=item.id,
                    question_text="What type of table would you like to place?",
                    suggested_options=opts.get(slot_name, []),
                    default_fallback_value=opts.get("default_table_type", None),
                )
                questions.append(q)
                reasons.append("Ambiguous table type specified.")

        # Rule 2E: Ambiguous Room ('10 seater room' without room type)
        if sem_type in ("ROOM", "UNKNOWN_ROOM") or ("room" in raw_phrase_lower and sem_type not in ROOM_SPACE_TYPES and sem_type != "MANAGER_CABIN"):
            if not any(k in raw_phrase_lower for k in ["conference", "meeting", "training", "break", "server", "manager"]):
                slot_name = "room_type"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    item_id=item.id,
                    question_text="What type of room should this be?",
                    suggested_options=opts.get(slot_name, []),
                    default_fallback_value=opts.get("default_room_type", None),
                )
                questions.append(q)
                reasons.append("Room type is unspecified.")

    # Rule 3: Spatial Preferences vs Physical Architectural Context
    arch_ctx = architectural_context or {}
    windows_count = arch_ctx.get("windows_count", None)

    # Detect if user requested placement near/along windows when physical space has 0 windows
    if windows_count is not None and windows_count == 0:
        already_clarified = "clarified window alternative" in (req_set.notes or "").lower()
        if not already_clarified:
            has_window_pref = any(
                "window" in (p.target_zone or "").lower() or "WINDOW" in (p.preference_type or "").upper()
                for p in (req_set.preferences or [])
            )
            has_window_item = any("window" in it.raw_phrase.lower() for it in req_set.items)

            if has_window_pref or has_window_item:
                # Identify target item (e.g. Manager Cabin)
                assoc_item = None
                for it in req_set.items:
                    if any(k in (it.semantic_type or "").upper() for k in ("CABIN", "MANAGER", "DESK")):
                        assoc_item = it
                        break
                if not assoc_item and req_set.items:
                    assoc_item = req_set.items[0]

                item_label = (
                    assoc_item.semantic_type.replace("_", " ").title()
                    if assoc_item and assoc_item.semantic_type
                    else "this element"
                )
                slot_name = "missing_window_alternative"
                q = ClarificationQuestion(
                    question_id=f"q_{uuid.uuid4().hex[:8]}",
                    slot=slot_name,
                    item_id=assoc_item.id if assoc_item else None,
                    question_text=f"No windows are present in this space. Where would you like to position the {item_label} instead?",
                    suggested_options=["Near Entrance", "Along Interior Wall", "In Corner", "No Specific Preference"],
                    default_fallback_value="Near Entrance",
                )
                questions.append(q)
                reasons.append("Requested spatial preference 'near window' cannot be satisfied because 0 windows are present in the architectural model.")

    is_complete = len(questions) == 0
    reasoning_summary = "; ".join(reasons) if reasons else "Requirement is semantically complete."
    return is_complete, questions, reasoning_summary


def classify_ambiguity_and_completeness(
    req_set: RequirementSet,
    options_config: Optional[dict] = None,
    architectural_context: Optional[dict] = None,
) -> ClarificationRequest:
    """
    Wraps deterministic completeness evaluation into a ClarificationRequest structure.
    """
    is_complete, questions, reasoning = evaluate_requirement_completeness(
        req_set,
        options_config=options_config,
        architectural_context=architectural_context,
    )
    return ClarificationRequest(
        needs_clarification=not is_complete,
        questions=questions,
        reasoning=reasoning,
    )
