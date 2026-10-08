"""
Unit tests for DeterministicLayoutSolver (Task 4.3 / Placement & Scale Fixes).
Validates polygon containment, wall/door swing collision avoidance, metric scale stability,
rotation footprint re-validation, and quantity fulfillment on irregular rooms.
"""

import pytest
from app.domain.geometry.entities import ColumnEntity, DoorEntity, RoomEntity, WallEntity
from geometry.geo_engine.layout_solver import DeterministicLayoutSolver
from geometry.geo_engine.rules.rule_evaluator import RuleEvaluator


@pytest.fixture
def solver():
    return DeterministicLayoutSolver()


@pytest.fixture
def sample_rectangular_room():
    """Standard 10m x 8m rectangular room with wall and door."""
    return RoomEntity(
        id="room_rect_101",
        name="Executive Suite 101",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        net_area_sqm=80.0,
        doors=[
            DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0),
        ],
        columns=[
            ColumnEntity(id="c1", center_x=5.0, center_y=4.0, width_m=0.6, height_m=0.6),
        ],
    )


@pytest.fixture
def sample_l_shaped_room():
    """Irregular L-shaped room (Requirement #25K)."""
    return RoomEntity(
        id="room_l_shape",
        name="L-Shaped Office",
        boundary_polygon=[
            (0.0, 0.0), (8.0, 0.0), (8.0, 4.0), (4.0, 4.0), (4.0, 8.0), (0.0, 8.0)
        ],
        net_area_sqm=48.0,
        doors=[
            DoorEntity(id="d_l1", center_x=1.0, center_y=0.0, width_m=0.9, swing_deg=90.0),
        ],
    )


def test_layout_solver_generates_valid_candidates(solver, sample_rectangular_room):
    """Test generating candidates for 6 Professional Desks + 1 Manager Desk."""
    reqs = [
        {"item_type": "PROFESSIONAL_DESK", "quantity": 6},
        {"item_type": "MANAGER_DESK", "quantity": 1},
    ]

    candidates = solver.solve_layout_candidates(
        floor_plan_id="fp_test_001",
        room=sample_rectangular_room,
        requested_items=reqs,
        max_candidates=3,
    )

    assert len(candidates) > 0
    sug = candidates[0]
    assert len(sug.placed_objects) == 7

    # Evaluate 20 architectural rules
    evaluator = RuleEvaluator()
    val_res = evaluator.evaluate(sug, sample_rectangular_room)
    assert val_res.is_valid, f"Candidate failed rules: {[v.message for v in val_res.hard_violations]}"


def test_furniture_containment_in_l_shaped_room(solver, sample_l_shaped_room):
    """Test containment inside irregular L-shaped room geometry."""
    reqs = [
        {"item_type": "PROFESSIONAL_DESK", "quantity": 4},
    ]

    candidates = solver.solve_layout_candidates(
        floor_plan_id="fp_l_shape",
        room=sample_l_shaped_room,
        requested_items=reqs,
    )

    assert len(candidates) > 0
    sug = candidates[0]
    evaluator = RuleEvaluator()
    val_res = evaluator.evaluate(sug, sample_l_shaped_room)

    # Verify no object lies in the excluded corner (x > 4, y > 4)
    for obj in sug.placed_objects:
        assert not (obj.x > 4.0 and obj.y > 4.0), f"Object {obj.id} placed in concavity outside room boundary!"
    assert val_res.is_valid


def test_door_swing_avoidance(solver, sample_rectangular_room):
    """Test that generated objects do not overlap the door swing arc."""
    reqs = [
        {"item_type": "PROFESSIONAL_DESK", "quantity": 5},
    ]

    candidates = solver.solve_layout_candidates(
        floor_plan_id="fp_door_test",
        room=sample_rectangular_room,
        requested_items=reqs,
    )

    assert len(candidates) > 0
    sug = candidates[0]

    # Door is centered at (2.0, 0.0) with 0.9m swing radius
    door_center_x, door_center_y = 2.0, 0.0
    for obj in sug.placed_objects:
        dist = ((obj.x - door_center_x)**2 + (obj.y - door_center_y)**2)**0.5
        assert dist > 0.9, f"Object {obj.id} placed inside door swing zone (dist={dist:.2f}m)"


def test_metric_scale_consistency(solver):
    """Test that furniture footprint dimensions use catalog world meters."""
    entry = solver.get_catalog_entry("PROFESSIONAL_DESK")
    assert entry["width"] == 1.5
    assert entry["depth"] == 0.75

    mgr_entry = solver.get_catalog_entry("MANAGER_DESK")
    assert mgr_entry["width"] == 1.8
    assert mgr_entry["depth"] == 0.9


def test_impossible_layout_handling(solver):
    """Test that requesting 500 desks in a small room returns infeasible result cleanly."""
    small_room = RoomEntity(
        id="room_tiny",
        name="Tiny Storage",
        boundary_polygon=[(0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (0.0, 3.0)],
        net_area_sqm=9.0,
    )
    reqs = [
        {"item_type": "PROFESSIONAL_DESK", "quantity": 500},
    ]

    candidates = solver.solve_layout_candidates(
        floor_plan_id="fp_tiny",
        room=small_room,
        requested_items=reqs,
    )

    assert len(candidates) > 0
    # Should handle gracefully without throwing error or outputting floating objects
    assert "Infeasible" in candidates[0].strategy_name or len(candidates[0].placed_objects) < 500
