"""
Unit test to verify Pydantic v2 contracts for Task 0.4.
Ensures RequirementSet, LayoutSuggestion, LayoutAction, and ValidationResult instantiate cleanly.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' package is discoverable from anywhere
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.schemas import (
    RequirementSet,
    RequirementItem,
    RequirementStatus,
    LayoutSuggestion,
    PlacedObject,
    LayoutMetrics,
    LayoutAction,
    ActionType,
    ValidationResult,
    ConstraintViolation,
    ViolationSeverity,
    ViolationType,
)
from app.ai.schemas import (
    ParsedRequirementOutput,
    ClarificationRequest,
    PlanningStrategyList,
    ChangeInterpreterOutput,
)


def test_requirement_set_instantiation():
    req_item = RequirementItem(
        id="item_1",
        raw_phrase="6 executive desks",
        resolved_catalog_item_id="cat_exec_desk_160",
        quantity=6,
        confidence=0.98,
    )
    req_set = RequirementSet(
        id="req_001",
        project_id="proj_101",
        floor_plan_id="fp_501",
        status=RequirementStatus.DRAFT,
        items=[req_item],
        target_density_seats=6,
    )
    assert req_set.id == "req_001"
    assert len(req_set.items) == 1
    assert req_set.items[0].quantity == 6


def test_layout_suggestion_instantiation():
    obj = PlacedObject(
        id="placed_1",
        catalog_item_id="cat_exec_desk_160",
        item_type="EXECUTIVE_DESK",
        x=5.2,
        y=3.4,
        rotation_deg=90.0,
        width=1.6,
        height=0.8,
    )
    metrics = LayoutMetrics(
        total_seats=6,
        used_floor_area_sqm=12.5,
        rule_compliance_score=1.0,
        composite_score=92.5,
    )
    suggestion = LayoutSuggestion(
        id="sug_001",
        floor_plan_id="fp_501",
        strategy_name="Perimeter Manager Strategy",
        placed_objects=[obj],
        metrics=metrics,
        explanation="Placed executive desks along outer perimeter wall.",
    )
    assert suggestion.id == "sug_001"
    assert suggestion.placed_objects[0].x == 5.2
    assert suggestion.metrics.composite_score == 92.5


def test_layout_action_instantiation():
    action = LayoutAction(
        action_id="act_001",
        action_type=ActionType.MOVE,
        target_object_ids=["placed_1"],
        target_phrase="manager desk",
        parameters={"delta_x": 0.5, "delta_y": 0.0},
    )
    assert action.action_type == ActionType.MOVE
    assert action.parameters["delta_x"] == 0.5


def test_validation_result_instantiation():
    violation = ConstraintViolation(
        id="v_001",
        violation_type=ViolationType.COLLISION,
        severity=ViolationSeverity.CRITICAL_HARD,
        affected_object_ids=["placed_1", "placed_2"],
        message="Executive desk overlaps with structural column",
    )
    result = ValidationResult(
        is_valid=False,
        total_violations_count=1,
        hard_violations=[violation],
        overall_rule_compliance_score=0.0,
    )
    assert not result.is_valid
    assert len(result.hard_violations) == 1
    assert result.hard_violations[0].violation_type == ViolationType.COLLISION


if __name__ == "__main__":
    test_requirement_set_instantiation()
    test_layout_suggestion_instantiation()
    test_layout_action_instantiation()
    test_validation_result_instantiation()
    print("ALL PYDANTIC DOMAIN CONTRACT TESTS PASSED SUCCESSFULLY!")
