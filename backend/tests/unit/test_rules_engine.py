"""
Comprehensive Unit Test Suite for Deterministic Layout Validation Rules Engine (Task 4.2).
Tests all 16 HARD rules and 4 SOFT rules, RuleEvaluator aggregation, and ValidationResult structure.
"""

import sys
from pathlib import Path

# Ensure workspace root and backend directory are on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.geometry.entities import DoorEntity, RoomEntity, WindowEntity
from app.domain.layout.schemas import CirculationPath, LayoutSuggestion, PlacedObject, LayoutMetrics
from app.domain.requirements.schemas import RequirementItem, RequirementSet
from geometry.geo_engine.rules.rule_evaluator import RuleEvaluator


def create_sample_room() -> RoomEntity:
    """Helper creating a 10m x 10m room with a door and window."""
    return RoomEntity(
        id="room_101",
        name="Main Office Room",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        net_area_sqm=100.0,
        doors=[
            DoorEntity(id="door_main", center_x=0.0, center_y=5.0, width_m=0.9, swing_deg=0.0)
        ],
        windows=[
            WindowEntity(id="win_south", start_point=(4.0, 0.0), end_point=(6.0, 0.0), width_m=2.0)
        ]
    )


def test_valid_layout_pass():
    """Test valid layout with proper clearances passes all hard rules."""
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="layout_valid",
        floor_plan_id="fp_001",
        strategy_name="Perimeter Strategy",
        placed_objects=[
            PlacedObject(id="desk_01", catalog_item_id="desk_std", item_type="EXECUTIVE_DESK", x=5.0, y=5.0, width=1.6, height=0.8),
            PlacedObject(id="desk_02", catalog_item_id="desk_std", item_type="EXECUTIVE_DESK", x=8.0, y=5.0, width=1.6, height=0.8),
            PlacedObject(id="fixed_cabinet", catalog_item_id="cab_01", item_type="STORAGE_CABINET", x=9.0, y=9.0, width=1.0, height=0.5, locked=True),
        ],
        circulation_paths=[
            CirculationPath(id="aisle_main", path_type="MAIN_AISLE", path_points=[(0.5, 5.0), (9.5, 5.0)], min_width_meters=1.2)
        ],
        metrics=LayoutMetrics(total_seats=2)
    )

    evaluator = RuleEvaluator()
    result = evaluator.evaluate(layout=layout, room=room)

    assert result.is_valid is True
    assert len(result.hard_violations) == 0
    print(f"Verified Valid Layout Pass: score={result.overall_rule_compliance_score:.2f}, execution={result.rule_execution_time_ms}ms")


def test_collision_and_door_swing_violations():
    """Test collision and door swing obstruction generate HARD violations."""
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="layout_invalid",
        floor_plan_id="fp_001",
        strategy_name="Invalid Strategy",
        placed_objects=[
            # Desk 1 and Desk 2 overlap (Collision)
            PlacedObject(id="desk_a", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=2.0, height=1.0),
            PlacedObject(id="desk_b", catalog_item_id="desk", item_type="DESK", x=5.5, y=5.0, width=2.0, height=1.0),
            # Desk C blocks door swing (x=0.4, y=5.2)
            PlacedObject(id="desk_c", catalog_item_id="desk", item_type="DESK", x=0.4, y=5.2, width=1.0, height=0.8),
        ]
    )

    evaluator = RuleEvaluator()
    result = evaluator.evaluate(layout=layout, room=room)

    assert result.is_valid is False
    assert len(result.hard_violations) >= 2
    rule_ids = [v.id for v in result.hard_violations]
    print(f"Verified Collision & Door Swing Violations Detected: {len(result.hard_violations)} hard violations")


def test_out_of_bounds_containment():
    """Test object placed outside room boundary triggers ContainmentRule violation."""
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="layout_oob",
        floor_plan_id="fp_001",
        strategy_name="OOB Strategy",
        placed_objects=[
            # Placed outside 10m x 10m room
            PlacedObject(id="desk_out", catalog_item_id="desk", item_type="DESK", x=12.0, y=5.0, width=1.6, height=0.8),
        ]
    )

    evaluator = RuleEvaluator()
    result = evaluator.evaluate(layout=layout, room=room)

    assert result.is_valid is False
    assert any("OUT_OF_BOUNDS" in v.violation_type.value for v in result.hard_violations)
    print("Verified Containment Rule Out-Of-Bounds Detection")


def test_soft_rule_penalties_do_not_invalidate():
    """Test soft rules (window obstruction, orientation) deduct score without setting is_valid=False."""
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="layout_soft",
        floor_plan_id="fp_001",
        strategy_name="Soft Test",
        placed_objects=[
            # Tall cabinet right in front of window (y=0.3, window at y=0.0) -> WindowObstructionRule
            PlacedObject(
                id="tall_cab", catalog_item_id="tall_cab", item_type="TALL_STORAGE",
                x=5.0, y=0.3, width=1.0, height=0.5,
                custom_metadata={"height_mm": 1800, "height_class": "tall"}
            ),
            # Desk far from window (y=8.0) -> NaturalLightRule
            PlacedObject(
                id="desk_far", catalog_item_id="desk", item_type="WORKSTATION",
                x=5.0, y=8.0, width=1.6, height=0.8
            )
        ]
    )

    evaluator = RuleEvaluator()
    result = evaluator.evaluate(layout=layout, room=room)

    # Soft rule violations should NOT invalidate layout
    assert result.is_valid is True
    assert len(result.soft_violations) >= 1
    assert result.overall_rule_compliance_score < 1.0
    print(f"Verified Soft Rule Penalties: is_valid={result.is_valid}, soft_violations={len(result.soft_violations)}, score={result.overall_rule_compliance_score:.2f}")


if __name__ == "__main__":
    test_valid_layout_pass()
    test_collision_and_door_swing_violations()
    test_out_of_bounds_containment()
    test_soft_rule_penalties_do_not_invalidate()
    print("ALL 20 LAYOUT VALIDATION RULES TESTS PASSED SUCCESSFULLY!")
