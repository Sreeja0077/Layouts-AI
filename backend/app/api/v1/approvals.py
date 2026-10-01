"""
Approvals & Audit Trail API router skeleton.
Handles 4-stage approval workflow transitions and immutable audit log queries.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.security import AuthenticatedUser, UserRole, require_roles

router = APIRouter()


@router.post("/transition", status_code=status.HTTP_200_OK)
async def transition_approval_stage(
    payload: Dict[str, Any],
    current_user: AuthenticatedUser = require_roles([UserRole.LAYOUT_EXEC, UserRole.LAYOUT_MGR, UserRole.SALES_MGR]),
) -> Dict[str, Any]:
    """Transition a floor plan revision to next approval stage (SUBMIT, APPROVE, REJECT)."""
    stage = payload.get("stage")
    decision = payload.get("decision")
    if not stage or not decision:
        raise HTTPException(status_code=400, detail="stage and decision are required")

    return {
        "approval_id": "appr_901",
        "stage": stage,
        "decision": decision,
        "status": "RECORDED",
        "actor_id": current_user.user_id,
        "actor_role": current_user.role.value,
        "content_hash": "sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
