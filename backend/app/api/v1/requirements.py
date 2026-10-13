"""
Requirements & Clarification API Router (Phase 8).
Translates natural-language requirements into structured semantic requirements,
evaluates completeness, triggers clarification questions, and persists state.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.ai.graph.requirement_workflow import get_requirement_workflow
from app.ai.schemas.structured_output import ClarificationQuestion
from app.domain.requirements.schemas import RequirementSet, RequirementStatus
from app.persistence.database import get_db
from app.persistence.models import ClarificationQuestionModel, RequirementSetModel

logger = logging.getLogger("app.api.v1.requirements")
router = APIRouter()


class CreateRequirementRequest(BaseModel):
    """Payload for submitting raw requirement text."""
    model_config = ConfigDict(extra="forbid")

    raw_text: str = Field(..., min_length=1, description="Raw natural-language requirement prompt")
    project_id: Optional[str] = Field("proj_default", description="Associated project ID")
    floor_plan_id: Optional[str] = Field("fp_default", description="Target floor plan ID")
    region_id: Optional[str] = Field(None, description="Optional target region ID from Task 6.3")
    architectural_context: Optional[Dict[str, Any]] = Field(None, description="Physical element counts or context")


class ClarifyRequirementRequest(BaseModel):
    """Payload for submitting an answer to a clarification question."""
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., min_length=1, description="User answer to clarification question")
    question_id: Optional[str] = Field(None, description="Question ID being answered")


class RequirementResponse(BaseModel):
    """Authoritative API response containing normalized requirement and clarification state."""
    model_config = ConfigDict(extra="forbid")

    requirement_set_id: str = Field(..., description="Unique RequirementSet ID")
    status: RequirementStatus = Field(..., description="Current requirement processing state")
    needs_clarification: bool = Field(..., description="True if blocking questions remain")
    questions: List[ClarificationQuestion] = Field(default_factory=list, description="Pending questions")
    reasoning: str = Field(..., description="Completeness or ambiguity explanation")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall parsing confidence")
    requirement_set: RequirementSet = Field(..., description="Underlying semantic requirement domain set")


def _safe_uuid(val: Optional[str]) -> Optional[str]:
    """Deterministically convert string to valid UUID format for DB column."""
    if not val:
        return None
    try:
        return str(uuid.UUID(val))
    except (ValueError, AttributeError):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val))


@router.post("/", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement_set(
    payload: CreateRequirementRequest,
    db: Session = Depends(get_db),
) -> RequirementResponse:
    """
    Parse raw user requirements, evaluate completeness, and initiate requirement lifecycle.
    """
    if not payload.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="raw_text requirement input cannot be empty",
        )

    req_id = str(uuid.uuid4())
    workflow = get_requirement_workflow()
    config = {"configurable": {"thread_id": req_id}}

    arch_ctx = dict(payload.architectural_context or {})
    # If architectural_context does not specify windows_count, look up active floor plan verification report
    if "windows_count" not in arch_ctx and payload.floor_plan_id:
        try:
            from app.api.v1.projects import ensure_uuid
            fp_uuid = ensure_uuid(payload.floor_plan_id)
            record = (
                db.query(FloorPlanSourceVersionModel)
                .filter(
                    (FloorPlanSourceVersionModel.floor_plan_id == payload.floor_plan_id)
                    | (FloorPlanSourceVersionModel.floor_plan_id == fp_uuid)
                )
                .order_by(FloorPlanSourceVersionModel.version_no.desc())
                .first()
            )
            if record and record.verification_report:
                elems = record.verification_report.get("all_elements_geometry") or []
                arch_ctx["windows_count"] = sum(1 for e in elems if "WINDOW" in (e.get("category") or "").upper())
                arch_ctx["doors_count"] = sum(1 for e in elems if "DOOR" in (e.get("category") or "").upper())
                arch_ctx["walls_count"] = sum(1 for e in elems if "WALL" in (e.get("category") or "").upper())
                arch_ctx["columns_count"] = sum(1 for e in elems if "COLUMN" in (e.get("category") or "").upper())
        except Exception:
            pass

    state_input = {
        "project_id": payload.project_id or "proj_default",
        "floor_plan_id": payload.floor_plan_id or "fp_default",
        "region_id": payload.region_id,
        "raw_text": payload.raw_text.strip(),
        "architectural_context": arch_ctx,
    }

    try:
        final_state = workflow.invoke(state_input, config)
    except RuntimeError as re:
        err_msg = str(re)
        logger.error(f"Provider or runtime error in requirement workflow: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY if "provider" in err_msg.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err_msg,
        )
    except Exception as e:
        logger.error(f"Error executing requirement workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process requirement: {str(e)}",
        )

    req_dict = final_state.get("requirement_set", {})
    req_set = RequirementSet.model_validate(req_dict)
    # Ensure ID consistency
    req_set.id = req_id

    needs_clarification = final_state.get("needs_clarification", False)
    questions = [
        ClarificationQuestion.model_validate(q)
        for q in final_state.get("questions", [])
    ]
    reasoning = final_state.get("reasoning", "Requirement processed.")

    confidence = 1.0
    if req_set.items:
        confidence = min(item.confidence for item in req_set.items)

    # Persist to database if available
    try:
        db_record = RequirementSetModel(
            id=_safe_uuid(req_id),
            floor_plan_id=_safe_uuid(req_set.floor_plan_id),
            region_id=_safe_uuid(req_set.room_id) if req_set.room_id else None,
            status=req_set.status.value,
            spec_json=req_set.model_dump(),
        )
        db.add(db_record)

        for q in questions:
            q_record = ClarificationQuestionModel(
                id=_safe_uuid(q.question_id),
                requirement_set_id=_safe_uuid(req_id),
                question_json=q.model_dump(),
                is_blocking=True,
            )
            db.add(q_record)

        db.commit()
    except Exception as db_err:
        logger.warning(f"Database persistence notice: {db_err}. Proceeding with in-memory state.")
        db.rollback()

    return RequirementResponse(
        requirement_set_id=req_id,
        status=req_set.status,
        needs_clarification=needs_clarification,
        questions=questions,
        reasoning=reasoning,
        confidence=confidence,
        requirement_set=req_set,
    )


@router.post("/{requirement_set_id}/clarify", response_model=RequirementResponse)
async def clarify_requirement_set(
    requirement_set_id: str,
    payload: ClarifyRequirementRequest,
    db: Session = Depends(get_db),
) -> RequirementResponse:
    """
    Resume requirement workflow with user's clarification answer and re-evaluate completeness.
    """
    workflow = get_requirement_workflow()
    config = {"configurable": {"thread_id": requirement_set_id}}

    resume_input = {
        "user_answer": payload.answer.strip(),
        "answered_question_id": payload.question_id,
    }

    try:
        updated_state = workflow.invoke(resume_input, config)
    except RuntimeError as re:
        err_msg = str(re)
        logger.error(f"Provider or runtime error resuming requirement workflow: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY if "provider" in err_msg.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err_msg,
        )
    except Exception as e:
        logger.error(f"Error resuming requirement workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to resume clarification workflow: {str(e)}",
        )

    req_dict = updated_state.get("requirement_set", {})
    req_set = RequirementSet.model_validate(req_dict)
    req_set.id = requirement_set_id

    needs_clarification = updated_state.get("needs_clarification", False)
    questions = [
        ClarificationQuestion.model_validate(q)
        for q in updated_state.get("questions", [])
    ]
    reasoning = updated_state.get("reasoning", "Requirement updated.")

    confidence = 1.0
    if req_set.items:
        confidence = min(item.confidence for item in req_set.items)

    # Update database record if present
    try:
        db_id = _safe_uuid(requirement_set_id)
        db_record = db.query(RequirementSetModel).filter(RequirementSetModel.id == db_id).first()
        if db_record:
            db_record.status = req_set.status.value
            db_record.spec_json = req_set.model_dump()
            db.commit()
    except Exception as db_err:
        logger.warning(f"Database update notice: {db_err}")
        db.rollback()

    return RequirementResponse(
        requirement_set_id=requirement_set_id,
        status=req_set.status,
        needs_clarification=needs_clarification,
        questions=questions,
        reasoning=reasoning,
        confidence=confidence,
        requirement_set=req_set,
    )


@router.get("/{requirement_set_id}", response_model=RequirementResponse)
async def get_requirement_set(
    requirement_set_id: str,
    db: Session = Depends(get_db),
) -> RequirementResponse:
    """
    Retrieve an existing RequirementSet and its clarification state by ID.
    """
    # 1. Try checkpointer state first
    workflow = get_requirement_workflow()
    config = {"configurable": {"thread_id": requirement_set_id}}
    state_snap = workflow.get_state(config)

    if state_snap and state_snap.values and state_snap.values.get("requirement_set"):
        vals = state_snap.values
        req_set = RequirementSet.model_validate(vals["requirement_set"])
        req_set.id = requirement_set_id
        questions = [
            ClarificationQuestion.model_validate(q)
            for q in vals.get("questions", [])
        ]
        return RequirementResponse(
            requirement_set_id=requirement_set_id,
            status=req_set.status,
            needs_clarification=vals.get("needs_clarification", False),
            questions=questions,
            reasoning=vals.get("reasoning", "Retrieved from state."),
            confidence=0.95,
            requirement_set=req_set,
        )

    # 2. Try database
    try:
        db_id = _safe_uuid(requirement_set_id)
        record = db.query(RequirementSetModel).filter(RequirementSetModel.id == db_id).first()
        if record and record.spec_json:
            req_set = RequirementSet.model_validate(record.spec_json)
            req_set.id = requirement_set_id
            questions = [
                ClarificationQuestion.model_validate(q.question_json)
                for q in record.clarification_questions
                if not q.user_answer
            ]
            return RequirementResponse(
                requirement_set_id=requirement_set_id,
                status=RequirementStatus(record.status),
                needs_clarification=len(questions) > 0,
                questions=questions,
                reasoning="Retrieved from persistent database.",
                confidence=0.95,
                requirement_set=req_set,
            )
    except Exception as db_err:
        logger.warning(f"Database lookup notice: {db_err}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"RequirementSet '{requirement_set_id}' not found.",
    )
