"""
Requirements & Clarification API router skeleton.
Handles RequirementSet creation, text/voice requirement extraction, and clarification Q&A.
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from app.domain.requirements.schemas import RequirementSet, RequirementStatus

router = APIRouter()


@router.post("/", response_model=RequirementSet, status_code=status.HTTP_201_CREATED)
async def create_requirement_set(payload: Dict[str, Any]) -> RequirementSet:
    """Parse raw text/voice requirements and create a RequirementSet."""
    raw_text = payload.get("raw_text", "")
    if not raw_text:
        raise HTTPException(status_code=400, detail="raw_text requirement input is required")

    return RequirementSet(
        id="req_001",
        project_id=payload.get("project_id", "proj_101"),
        floor_plan_id=payload.get("floor_plan_id", "fp_501"),
        status=RequirementStatus.DRAFT,
        items=[],
        notes=f"Parsed from input: {raw_text}",
    )


@router.get("/{requirement_set_id}", response_model=RequirementSet)
async def get_requirement_set(requirement_set_id: str) -> RequirementSet:
    """Retrieve an existing RequirementSet by ID."""
    return RequirementSet(
        id=requirement_set_id,
        project_id="proj_101",
        floor_plan_id="fp_501",
        status=RequirementStatus.NORMALIZED,
        items=[],
    )
