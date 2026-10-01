"""
Layout Generation & Iterative Edit API router skeleton.
Handles candidate proposal generation, OR-Tools CP-SAT placement, and natural language layout modification.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from app.domain.layout.schemas import LayoutSuggestion, LayoutAction, ActionType

router = APIRouter()


@router.post("/generate", response_model=List[LayoutSuggestion], status_code=status.HTTP_200_OK)
async def generate_layout_candidates(payload: Dict[str, Any]) -> List[LayoutSuggestion]:
    """Generate 3-5 spatial layout candidates using optimization strategies."""
    floor_plan_id = payload.get("floor_plan_id")
    if not floor_plan_id:
        raise HTTPException(status_code=400, detail="floor_plan_id is required")

    return [
        LayoutSuggestion(
            id="sug_001",
            floor_plan_id=floor_plan_id,
            strategy_name="Perimeter High-Density Strategy",
            placed_objects=[],
            explanation="Arranged desks along perimeter walls for maximum natural lighting.",
        ),
        LayoutSuggestion(
            id="sug_002",
            floor_plan_id=floor_plan_id,
            strategy_name="Two-Row Cluster Strategy",
            placed_objects=[],
            explanation="Grouped workstations into central collaborative pods.",
        ),
    ]


@router.post("/apply-action", response_model=Dict[str, Any])
async def apply_layout_action(action: LayoutAction) -> Dict[str, Any]:
    """Apply an iterative modification action (MOVE, ADD, ROTATE, LOCK) to a layout revision."""
    return {
        "status": "APPLIED",
        "action_id": action.action_id,
        "action_type": action.action_type,
        "message": f"Successfully applied action {action.action_type.value}",
    }
