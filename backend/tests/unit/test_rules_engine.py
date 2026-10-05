"""
Comprehensive Unit Test Suite for Deterministic Architectural Layout Validation Rules Engine (Task 4.2).
Tests all 16 HARD rules and 4 SOFT rules individually, fault isolation, SHA-256 deterministic violation IDs,
custom ruleset config deep-copy isolation, and domain contract alignment.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.geometry.entities import ColumnEntity, DoorEntity, ExistingFurnitureEntity, RoomEntity, WindowEntity
from app.domain.geometry.schemas import ConstraintViolation, ValidationResult, ViolationSeverity, ViolationType
from app.domain.layout.schemas import CirculationPath, LayoutMetrics, LayoutSuggestion, PlacedObject
from app.domain.requirements.schemas import RequirementItem, RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import DEFAULT_RULESET_CONFIG, get_ruleset_config
from geometry.geo_engine.rules.rule_evaluator import RuleEvaluator

from geometry.geo_engine.rules.geometry import (
    GeometryValidityRule,
    CollisionRule,
    ContainmentRule,
    FixedObjectIntegrityRule,
)
from geometry.geo_engine.rules.circulation import (
    ClearanceRule,
    AisleWidthRule,
    AccessibilityRule,
    EgressRule,
    DoorSwingRule,
    EntranceObstructionRule,
)
from geometry.geo_engine.rules.requirements import (
    RequirementComplianceRule,
    QuantityFulfillmentRule,
    CapacityRule,
    BundleIntegrityRule,
)
from geometry.geo_engine.rules.spatial import ZoneRule, ConnectivityRule, OrientationRule
from geometry.geo_engine.rules.design import WindowObstructionRule, WallProximityRule, NaturalLightRule


def create_sample_room() -> RoomEntity:
    """Helper creating a 10m x 10m room with a door, window, column, and retained furniture."""
    return RoomEntity(
        id="room_101",
        name="Main Office Room",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        net_area_sqm=100.0,
        doors=[
            DoorEntity(id="door_main", center_x=5.0, center_y=0.0, width_m=1.0, swing_deg=90.0)
        ],
        windows=[
            WindowEntity(id="win_south", start_point=(4.0, 10.0), end_point=(6.0, 10.0), width_m=2.0)
        ],
        columns=[
            ColumnEntity(id="col_center", center_x=8.0, center_y=8.0, width_m=0.6, height_m=0.6)
        ],
        existing_furniture=[
            ExistingFurnitureEntity(id="retained_desk_01", catalog_item_id="desk_exec", position=(2.0, 2.0), rotation=0.0, keep_flag=True)
        ]
    )


# --- 1-4. GEOMETRY RULES TESTS ---

def test_1_valid_geometry_passes():
    rule = GeometryValidityRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk_std", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 0


def test_2_invalid_room_polygon_fails():
    rule = GeometryValidityRule()
    invalid_room = RoomEntity(id="r_inv", name="Bad Room", boundary_polygon=[(0.0, 0.0), (10.0, 0.0)], net_area_sqm=10.0)
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])
    violations = rule.evaluate(layout=layout, room=invalid_room)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.OUT_OF_BOUNDS


def test_3_invalid_object_dimension_fails():
    rule = GeometryValidityRule()
    room = create_sample_room()
    obj = PlacedObject(id="d_bad", catalog_item_id="desk_std", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8)
    obj.width = -1.0
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[obj]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.COLLISION


def test_4_rotated_object_footprint_validity():
    rule = GeometryValidityRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_rot", catalog_item_id="desk_std", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, rotation_deg=45.0)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 0


# --- 5-8. COLLISION RULE TESTS ---

def test_5_overlapping_furniture_detected():
    rule = CollisionRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk_std", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8),
            PlacedObject(id="d2", catalog_item_id="desk_std", item_type="DESK", x=5.2, y=5.2, width=1.6, height=0.8),
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.COLLISION
    assert set(violations[0].affected_object_ids) == {"d1", "d2"}


def test_6_boundary_touching_does_not_count_as_collision():
    rule = CollisionRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk_std", item_type="DESK", x=1.0, y=1.0, width=2.0, height=1.0),
            PlacedObject(id="d2", catalog_item_id="desk_std", item_type="DESK", x=3.0, y=1.0, width=2.0, height=1.0),
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


def test_7_object_vs_column_collision():
    rule = CollisionRule()
    room = create_sample_room()  # Column at (8.0, 8.0), 0.6m x 0.6m
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d_col", catalog_item_id="desk_std", item_type="DESK", x=8.0, y=8.0, width=1.6, height=0.8)
        ]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) >= 1
    assert violations[0].violation_type == ViolationType.COLUMN_COLLISION


def test_8_attached_collision_policy():
    rule = CollisionRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="screen", catalog_item_id="scr_01", item_type="SCREEN", x=5.0, y=5.0, width=1.0, height=0.2, custom_metadata={"collision_policy": "attached"}),
            PlacedObject(id="desk", catalog_item_id="desk_std", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8),
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


# --- 9-12. CONTAINMENT RULE TESTS ---

def test_9_object_fully_inside_room_passes():
    rule = ContainmentRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk_std", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 0


def test_10_object_outside_room_fails():
    rule = ContainmentRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_out", catalog_item_id="desk_std", item_type="DESK", x=15.0, y=15.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.OUT_OF_BOUNDS


def test_11_object_crossing_concave_boundary_fails():
    rule = ContainmentRule()
    l_room = RoomEntity(id="l_room", name="L Room", boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)], net_area_sqm=75.0)
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_corner", catalog_item_id="desk_std", item_type="DESK", x=7.5, y=7.5, width=2.0, height=2.0)]
    )
    violations = rule.evaluate(layout=layout, room=l_room)
    assert len(violations) == 1


def test_12_object_intersecting_free_space_hole_fails():
    rule = ContainmentRule()
    room = create_sample_room()  # Column obstacle at (8.0, 8.0)
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_hole", catalog_item_id="desk_std", item_type="DESK", x=8.0, y=8.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1


# --- 13-16. FIXED OBJECT INTEGRITY RULE TESTS ---

def test_13_retained_existing_furniture_unchanged_passes():
    rule = FixedObjectIntegrityRule()
    room = create_sample_room()  # retained_desk_01 at (2.0, 2.0), rot 0.0
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="retained_desk_01", catalog_item_id="desk_exec", item_type="DESK", x=2.0, y=2.0, rotation_deg=0.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 0


def test_14_retained_furniture_moved_fails():
    rule = FixedObjectIntegrityRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="retained_desk_01", catalog_item_id="desk_exec", item_type="DESK", x=3.0, y=2.0, rotation_deg=0.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.COLLISION


def test_15_retained_furniture_rotated_fails():
    rule = FixedObjectIntegrityRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="retained_desk_01", catalog_item_id="desk_exec", item_type="DESK", x=2.0, y=2.0, rotation_deg=45.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1


def test_16_movable_existing_furniture_can_move():
    rule = FixedObjectIntegrityRule()
    movable_room = RoomEntity(
        id="r1", name="Room", boundary_polygon=[(0,0), (10,0), (10,10), (0,10)], net_area_sqm=100.0,
        existing_furniture=[ExistingFurnitureEntity(id="temp_chair", catalog_item_id="chair_std", position=(1.0, 1.0), rotation=0.0, keep_flag=False)]
    )
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])
    violations = rule.evaluate(layout=layout, room=movable_room)
    assert len(violations) == 0


# --- 17-20. CLEARANCE RULE TESTS ---

def test_17_insufficient_rear_clearance_detected():
    rule = ClearanceRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, clearance_back=0.8),
            PlacedObject(id="d2", catalog_item_id="desk", item_type="DESK", x=5.0, y=4.4, width=1.6, height=0.8),  # Obstructs d1 rear clearance
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) >= 1
    assert violations[0].violation_type == ViolationType.CLEARANCE_OVERLAP


def test_18_insufficient_front_clearance_detected():
    rule = ClearanceRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="cab1", catalog_item_id="cab", item_type="CABINET", x=5.0, y=5.0, width=1.0, height=0.5, clearance_front=0.9),
            PlacedObject(id="box2", catalog_item_id="box", item_type="BOX", x=5.0, y=5.5, width=0.8, height=0.5),
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) >= 1


def test_19_rotated_clearance_envelope_works():
    rule = ClearanceRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, rotation_deg=90.0, clearance_front=0.9),
            PlacedObject(id="d2", catalog_item_id="desk", item_type="DESK", x=5.8, y=5.0, width=0.8, height=0.8),
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) >= 1


def test_20_pair_violations_are_not_duplicated():
    rule = ClearanceRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, clearance_front=1.0),
            PlacedObject(id="d2", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.3, width=1.6, height=0.8, clearance_front=1.0),
        ]
    )
    violations = rule.evaluate(layout=layout)
    # Deduplicated pair key means exactly 1 clearance overlap reported for pair (d1, d2)
    assert len(violations) == 1


# --- 21-23. AISLE WIDTH RULE TESTS ---

def test_21_main_aisle_below_minimum_fails():
    rule = AisleWidthRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        circulation_paths=[CirculationPath(id="p1", path_type="MAIN_AISLE", min_width_meters=1.0, path_points=[(0,5), (10,5)])]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.EGRESS_BLOCKAGE


def test_22_main_aisle_at_minimum_passes():
    rule = AisleWidthRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        circulation_paths=[CirculationPath(id="p1", path_type="MAIN_AISLE", min_width_meters=1.2, path_points=[(0,5), (10,5)])]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


def test_23_secondary_aisle_below_minimum_fails():
    rule = AisleWidthRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        circulation_paths=[CirculationPath(id="p2", path_type="SECONDARY_AISLE", min_width_meters=0.8, path_points=[(0,5), (10,5)])]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1


# --- 24-25. ACCESSIBILITY RULE TESTS ---

def test_24_accessible_path_below_configured_width_fails():
    rule = AccessibilityRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        circulation_paths=[CirculationPath(id="p1", path_type="ACCESSIBLE_ROUTE", min_width_meters=0.8, path_points=[(0,5), (10,5)])]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1


def test_25_turning_circle_obstruction_fails():
    rule = AccessibilityRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_block", catalog_item_id="desk", item_type="DESK", x=0.0, y=5.0, width=1.6, height=0.8)],
        circulation_paths=[CirculationPath(id="p1", path_type="MAIN_AISLE", min_width_meters=1.2, path_points=[(0.0, 5.0), (10.0, 5.0)])]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) >= 1


# --- 26-27. EGRESS RULE TESTS ---

def test_26_door_threshold_obstruction_fails():
    rule = EgressRule()
    room = create_sample_room()  # Door at (5.0, 0.0)
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_door_block", catalog_item_id="desk", item_type="DESK", x=5.0, y=0.2, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) >= 1
    assert violations[0].violation_type == ViolationType.EGRESS_BLOCKAGE


def test_27_valid_declared_door_connected_path_passes():
    rule = EgressRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=2.0, y=5.0, width=1.6, height=0.8)],
        circulation_paths=[CirculationPath(id="p1", path_type="MAIN_AISLE", min_width_meters=1.2, path_points=[(5.0, 0.5), (5.0, 8.0)])]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 0


# --- 28. DOOR SWING RULE TEST ---

def test_28_door_swing_obstruction_detected():
    rule = DoorSwingRule()
    room = create_sample_room()  # Door at (5.0, 0.0), swing arc in +x/+y quadrant
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_swing_block", catalog_item_id="desk", item_type="DESK", x=5.4, y=0.4, width=0.8, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.DOOR_SWING_OBSTRUCTION


# --- 29. ENTRANCE OBSTRUCTION RULE TEST ---

def test_29_entrance_approach_blockage_detected():
    rule = EntranceObstructionRule()
    room = create_sample_room()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d_entrance_block", catalog_item_id="desk", item_type="DESK", x=5.0, y=0.3, width=1.0, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.CLEARANCE_OVERLAP


# --- 30-31. REQUIREMENT COMPLIANCE RULE TESTS ---

def test_30_exact_resolved_catalog_item_passes():
    rule = RequirementComplianceRule()
    reqs = RequirementSet(
        id="req1", project_id="p1", floor_plan_id="fp1",
        items=[RequirementItem(id="i1", raw_phrase="Executive Desk", resolved_catalog_item_id="desk_exec", quantity=1)]
    )
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk_exec", item_type="EXECUTIVE_DESK", x=5.0, y=5.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout, requirements=reqs)
    assert len(violations) == 0


def test_31_missing_resolved_catalog_item_fails():
    rule = RequirementComplianceRule()
    reqs = RequirementSet(
        id="req1", project_id="p1", floor_plan_id="fp1",
        items=[RequirementItem(id="i1", raw_phrase="Executive Desk", resolved_catalog_item_id="desk_exec", quantity=1)]
    )
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])
    violations = rule.evaluate(layout=layout, requirements=reqs)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.SPACING_VIOLATION


# --- 32-34. QUANTITY FULFILLMENT RULE TESTS ---

def test_32_quantity_shortfall_reject_mode_fails():
    rule = QuantityFulfillmentRule()
    reqs = RequirementSet(
        id="req1", project_id="p1", floor_plan_id="fp1",
        items=[RequirementItem(id="i1", raw_phrase="Standard Desk", resolved_catalog_item_id="desk_std", quantity=5)]
    )
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk_std", item_type="DESK", x=1.0, y=1.0, width=1.0, height=0.8)]
    )
    cfg = {"quantity": {"partial_fulfillment": {"mode": "reject"}}}
    violations = rule.evaluate(layout=layout, requirements=reqs, config=cfg)
    assert len(violations) == 1
    assert violations[0].severity == ViolationSeverity.CRITICAL_HARD


def test_33_quantity_shortfall_warning_mode():
    rule = QuantityFulfillmentRule()
    reqs = RequirementSet(
        id="req1", project_id="p1", floor_plan_id="fp1",
        items=[RequirementItem(id="i1", raw_phrase="Standard Desk", resolved_catalog_item_id="desk_std", quantity=5)]
    )
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk_std", item_type="DESK", x=1.0, y=1.0, width=1.0, height=0.8)]
    )
    cfg = {"quantity": {"partial_fulfillment": {"mode": "warning"}}}
    violations = rule.evaluate(layout=layout, requirements=reqs, config=cfg)
    assert len(violations) == 1
    assert violations[0].severity == ViolationSeverity.WARNING_SOFT


def test_34_quantity_allow_mode_passes():
    rule = QuantityFulfillmentRule()
    reqs = RequirementSet(
        id="req1", project_id="p1", floor_plan_id="fp1",
        items=[RequirementItem(id="i1", raw_phrase="Standard Desk", resolved_catalog_item_id="desk_std", quantity=5)]
    )
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])
    cfg = {"quantity": {"partial_fulfillment": {"mode": "allow"}}}
    violations = rule.evaluate(layout=layout, requirements=reqs, config=cfg)
    assert len(violations) == 0


# --- 35-36. CAPACITY RULE TESTS ---

def test_35_capacity_shortfall_detected():
    rule = CapacityRule()
    reqs = RequirementSet(id="req1", project_id="p1", floor_plan_id="fp1", target_density_seats=10)
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=1.0, y=1.0, width=1.0, height=0.8, custom_metadata={"capacity": 4})],
        metrics=LayoutMetrics(total_seats=4)
    )
    violations = rule.evaluate(layout=layout, requirements=reqs)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.SPACING_VIOLATION


def test_36_capacity_target_absent_passes():
    rule = CapacityRule()
    reqs = RequirementSet(id="req1", project_id="p1", floor_plan_id="fp1", target_density_seats=None)
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])
    violations = rule.evaluate(layout=layout, requirements=reqs)
    assert len(violations) == 0


# --- 37. BUNDLE INTEGRITY RULE TEST ---

def test_37_bundle_missing_component_detected():
    rule = BundleIntegrityRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(
                id="desk_b1", catalog_item_id="desk_bundle", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8,
                custom_metadata={"bundle_id": "b_101", "required_bundle_components": ["DESK", "CHAIR"]}
            )
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.SPACING_VIOLATION


# --- 38-41. ZONE / CONNECTIVITY RULE TESTS ---

def test_38_forbidden_zone_detected():
    rule = ZoneRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, custom_metadata={"zone_id": "circulation", "disallowed_zones": ["circulation"]})
        ]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.OUT_OF_BOUNDS


def test_39_no_zone_metadata_passes():
    rule = ZoneRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


def test_40_invalid_declared_connectivity_detected():
    rule = ConnectivityRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, custom_metadata={"requires_connectivity": True})],
        circulation_paths=[]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 1


def test_41_no_connectivity_requirement_passes():
    rule = ConnectivityRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8)]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


# --- 42-46. SOFT DESIGN RULE TESTS ---

def test_42_orientation_within_tolerance_passes():
    rule = OrientationRule()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, rotation_deg=10.0, custom_metadata={"preferred_rotation_deg": 0.0})]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


def test_43_orientation_circular_angle_calculation():
    rule = OrientationRule()
    # 355° vs preferred 5° -> true circular diff is 10° (within 15° tolerance)
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8, rotation_deg=355.0, custom_metadata={"preferred_rotation_deg": 5.0})]
    )
    violations = rule.evaluate(layout=layout)
    assert len(violations) == 0


def test_44_window_obstruction_warning():
    rule = WindowObstructionRule()
    room = create_sample_room()  # Window at y=10.0 between x=4 and x=6
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="cab_tall", catalog_item_id="cab", item_type="CABINET", x=5.0, y=9.5, width=1.0, height=0.6, custom_metadata={"height_mm": 1800})]
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].severity == ViolationSeverity.WARNING_SOFT
    assert violations[0].violation_type == ViolationType.WINDOW_OBSTRUCTION


def test_45_wall_proximity_warning():
    rule = WallProximityRule()
    room = create_sample_room()  # Perimeter walls at x=0, x=10, y=0, y=10
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="cab1", catalog_item_id="cab", item_type="STORAGE_CABINET", x=0.52, y=5.0, width=1.0, height=0.5, rotation_deg=0.0)]  # 20mm gap to x=0 wall
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].severity == ViolationSeverity.WARNING_SOFT


def test_46_natural_light_warning():
    rule = NaturalLightRule()
    room = create_sample_room()  # Window at y=10.0
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[PlacedObject(id="desk_far", catalog_item_id="desk", item_type="DESK", x=5.0, y=1.0, width=1.6, height=0.8)]  # 9.0m from window (> 6.0m max)
    )
    violations = rule.evaluate(layout=layout, room=room)
    assert len(violations) == 1
    assert violations[0].severity == ViolationSeverity.WARNING_SOFT


# --- 47-55. EVALUATOR MANIFEST, ISOLATION, DETERMINISM TESTS ---

def test_47_all_16_hard_rules_present():
    evaluator = RuleEvaluator()
    assert len(evaluator.hard_rules) == 16


def test_48_all_4_soft_rules_present():
    evaluator = RuleEvaluator()
    assert len(evaluator.soft_rules) == 4


def test_49_total_exactly_20_rules():
    evaluator = RuleEvaluator()
    assert len(evaluator.hard_rules) + len(evaluator.soft_rules) == 20


def test_50_hard_rule_exception_becomes_hard_violation():
    evaluator = RuleEvaluator()
    mock_rule = MagicMock(spec=BaseRule)
    mock_rule.rule_id = "mock_hard_fail"
    mock_rule.severity = ViolationSeverity.CRITICAL_HARD
    mock_rule.evaluate.side_effect = RuntimeError("Forced hard failure")
    mock_rule.create_violation.side_effect = lambda **kwargs: ConstraintViolation(
        id="mock_hard_id", violation_type=kwargs.get("violation_type"), severity=ViolationSeverity.CRITICAL_HARD, message=kwargs.get("message")
    )

    evaluator.hard_rules.insert(0, mock_rule)
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])

    res = evaluator.evaluate(layout=layout)
    assert res.is_valid is False
    assert any(v.violation_type == ViolationType.RULE_EXECUTION_ERROR for v in res.hard_violations)


def test_51_soft_rule_exception_becomes_soft_warning():
    evaluator = RuleEvaluator()
    mock_rule = MagicMock(spec=BaseRule)
    mock_rule.rule_id = "mock_soft_fail"
    mock_rule.severity = ViolationSeverity.WARNING_SOFT
    mock_rule.evaluate.side_effect = RuntimeError("Forced soft failure")
    mock_rule.create_violation.side_effect = lambda **kwargs: ConstraintViolation(
        id="mock_soft_id", violation_type=kwargs.get("violation_type"), severity=ViolationSeverity.WARNING_SOFT, message=kwargs.get("message"), penalty_score=5.0
    )

    evaluator.soft_rules.insert(0, mock_rule)
    layout = LayoutSuggestion(id="l1", floor_plan_id="fp1", strategy_name="s1", placed_objects=[])

    res = evaluator.evaluate(layout=layout)
    assert res.is_valid is True  # Soft exception alone does NOT invalidate layout
    assert any(v.violation_type == ViolationType.RULE_EXECUTION_ERROR for v in res.soft_violations)


def test_52_later_rules_still_execute_after_exception():
    evaluator = RuleEvaluator()
    mock_failing_rule = MagicMock(spec=BaseRule)
    mock_failing_rule.rule_id = "failing_hard"
    mock_failing_rule.severity = ViolationSeverity.CRITICAL_HARD
    mock_failing_rule.evaluate.side_effect = RuntimeError("Broken rule")
    mock_failing_rule.create_violation.side_effect = lambda **kwargs: ConstraintViolation(
        id="fail_id", violation_type=kwargs.get("violation_type"), severity=ViolationSeverity.CRITICAL_HARD, message=kwargs.get("message")
    )

    evaluator.hard_rules.insert(0, mock_failing_rule)
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8),
            PlacedObject(id="d2", catalog_item_id="desk", item_type="DESK", x=5.1, y=5.1, width=1.6, height=0.8),
        ]
    )

    res = evaluator.evaluate(layout=layout)
    # Both the failing rule exception violation AND later CollisionRule violations exist!
    assert len(res.hard_violations) >= 2


def test_53_deterministic_violation_ids():
    evaluator = RuleEvaluator()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8),
            PlacedObject(id="d2", catalog_item_id="desk", item_type="DESK", x=5.1, y=5.1, width=1.6, height=0.8),
        ]
    )

    res1 = evaluator.evaluate(layout=layout)
    res2 = evaluator.evaluate(layout=layout)

    ids1 = [v.id for v in res1.hard_violations]
    ids2 = [v.id for v in res2.hard_violations]
    assert ids1 == ids2


def test_54_deterministic_violation_ordering():
    evaluator = RuleEvaluator()
    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        placed_objects=[
            PlacedObject(id="d1", catalog_item_id="desk", item_type="DESK", x=5.0, y=5.0, width=1.6, height=0.8),
            PlacedObject(id="d2", catalog_item_id="desk", item_type="DESK", x=5.1, y=5.1, width=1.6, height=0.8),
        ]
    )

    for _ in range(100):
        res = evaluator.evaluate(layout=layout)
        hard_ids = [v.id for v in res.hard_violations]
        assert hard_ids == sorted(hard_ids)


def test_55_custom_ruleset_overrides_work():
    custom_cfg = {"circulation": {"main_aisle_min_mm": 1500}}  # Override main aisle to 1.5m
    evaluator = RuleEvaluator(custom_ruleset_config=custom_cfg)

    layout = LayoutSuggestion(
        id="l1", floor_plan_id="fp1", strategy_name="s1",
        circulation_paths=[CirculationPath(id="p1", path_type="MAIN_AISLE", min_width_meters=1.3, path_points=[(0,5), (10,5)])]
    )
    res = evaluator.evaluate(layout=layout)
    assert res.is_valid is False
    assert any("below required minimum of 1.50m" in v.message for v in res.hard_violations)

    # Global default config must remain unmutated (1200mm)
    assert DEFAULT_RULESET_CONFIG["circulation"]["main_aisle_min_mm"] == 1200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
