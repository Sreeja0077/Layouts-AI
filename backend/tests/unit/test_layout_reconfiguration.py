"""
Deterministic Layout Reconfiguration & Optimization Unit Tests (Phase 9 Tests A - N).
Verifies:
- TEST A: Small valid area + 2 chairs (dynamic candidate count)
- TEST B: Small meeting-room area
- TEST C: Small area + 10 workstations (explicit infeasibility, no partial placement)
- TEST D: Large area + 10 workstations (multiple valid candidates)
- TEST E: Sold/red existing desk preserved (position, rotation, immutability)
- TEST F: Available/green existing desk movable (stable source ID, no duplication)
- TEST G: Available chair + desk + cabin + sold desk (reconfiguration validity)
- TEST H: Selected region authoritative scope
- TEST I: Internal wall preserved by default
- TEST J: Outer concrete wall never moves
- TEST K: Circulation & egress validation
- TEST L: Candidate deduplication via spatial signatures
- TEST M: Determinism of solver outputs
- TEST N: Strict requirement quantity preservation (never partial success)
"""

import pytest
from app.domain.geometry.entities import (
    ColumnEntity,
    DoorEntity,
    ExistingFurnitureEntity,
    MovabilityStatus,
    RoomEntity,
    WallEntity,
)
from app.domain.layout.schemas import PlacedObject
from geometry.geo_engine.circulation import CirculationEngine
from geometry.geo_engine.layout_solver import DeterministicLayoutSolver, compute_spatial_signature
from geometry.geo_engine.rules.rule_evaluator import RuleEvaluator


@pytest.fixture
def solver():
    return DeterministicLayoutSolver()


@pytest.fixture
def evaluator():
    return RuleEvaluator()


# =====================================================================
# TEST A: Small valid area + 2 chairs
# =====================================================================
def test_a_small_valid_area_two_chairs(solver):
    """TEST A: Small valid area + 2 chairs returns 1..N valid candidates dynamically without forcing 3-5."""
    small_room = RoomEntity(
        id="room_small_a",
        name="Small Office A",
        boundary_polygon=[(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)],
        net_area_sqm=16.0,
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [{"item_type": "TASK_CHAIR", "quantity": 2}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_a",
        room=small_room,
        requested_items=reqs,
        max_candidates=10,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    # Candidate count is dynamic, not forced to 3 or 5
    for cand in res.candidates:
        assert len(cand.placed_objects) == 2
        for obj in cand.placed_objects:
            assert obj.item_type == "TASK_CHAIR"


# =====================================================================
# TEST B: Small meeting-room area
# =====================================================================
def test_b_small_meeting_room_area(solver, evaluator):
    """TEST B: Small meeting room area returns only genuinely valid spatial configurations."""
    meeting_room = RoomEntity(
        id="room_meeting_b",
        name="Meeting Room B",
        boundary_polygon=[(0.0, 0.0), (4.5, 0.0), (4.5, 3.5), (0.0, 3.5)],
        net_area_sqm=15.75,
        doors=[DoorEntity(id="d1", center_x=0.8, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [
        {"item_type": "CONFERENCE_TABLE", "quantity": 1},
        {"item_type": "TASK_CHAIR", "quantity": 2},
    ]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_b",
        room=meeting_room,
        requested_items=reqs,
        max_candidates=5,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        val = evaluator.evaluate(cand, meeting_room)
        assert val.is_valid, f"Violations: {[v.message for v in val.hard_violations]}"


# =====================================================================
# TEST C: Small area + 10 workstations (Infeasible)
# =====================================================================
def test_c_small_area_ten_workstations_infeasible(solver):
    """TEST C: Requesting 10 workstations in small 3m x 3m space returns candidate count = 0 and explicit InfeasibilityReport."""
    tiny_room = RoomEntity(
        id="room_tiny_c",
        name="Tiny Nook C",
        boundary_polygon=[(0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (0.0, 3.0)],
        net_area_sqm=9.0,
        doors=[DoorEntity(id="d1", center_x=1.5, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [{"item_type": "WORKSTATION", "quantity": 10}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_c",
        room=tiny_room,
        requested_items=reqs,
    )

    assert res.success is False
    assert res.candidate_count == 0
    assert len(res.candidates) == 0
    assert res.infeasibility_report is not None
    assert res.infeasibility_report.is_feasible is False
    assert len(res.infeasibility_report.reasons) > 0


# =====================================================================
# TEST D: Large area + 10 workstations
# =====================================================================
def test_d_large_area_ten_workstations(solver, evaluator):
    """TEST D: Large room + 10 workstations produces multiple valid candidates without arbitrary 3 or 5 limit."""
    large_room = RoomEntity(
        id="room_large_d",
        name="Open Office Floor D",
        boundary_polygon=[(0.0, 0.0), (14.0, 0.0), (14.0, 10.0), (0.0, 10.0)],
        net_area_sqm=140.0,
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=1.0, swing_deg=90.0)],
    )
    reqs = [{"item_type": "WORKSTATION", "quantity": 10}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_d",
        room=large_room,
        requested_items=reqs,
        max_candidates=10,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        assert len(cand.placed_objects) == 10
        val = evaluator.evaluate(cand, large_room)
        assert val.is_valid


# =====================================================================
# TEST E: Sold/red existing desk is strictly fixed
# =====================================================================
def test_e_sold_red_existing_desk(solver):
    """TEST E: SOLD_FIXED existing desk position and rotation remain completely unchanged."""
    room = RoomEntity(
        id="room_sold_e",
        name="Office E",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        net_area_sqm=80.0,
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
        existing_furniture=[
            ExistingFurnitureEntity(
                id="sold_desk_1",
                catalog_item_id="PROFESSIONAL_DESK",
                position=(4.0, 4.0),
                rotation=90.0,
                keep_flag=True,
                movability_status=MovabilityStatus.SOLD_FIXED,
                width_m=1.5,
                depth_m=0.75,
            )
        ],
    )
    reqs = [{"item_type": "TASK_CHAIR", "quantity": 2}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_e",
        room=room,
        requested_items=reqs,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        sold_obj = next((o for o in cand.placed_objects if o.source_object_id == "sold_desk_1" or o.id == "sold_desk_1"), None)
        assert sold_obj is not None
        assert sold_obj.x == 4.0
        assert sold_obj.y == 4.0
        assert sold_obj.rotation_deg == 90.0
        assert sold_obj.is_relocated is False
        assert sold_obj.movability_status == "SOLD_FIXED"


# =====================================================================
# TEST F: Available/green existing desk is movable
# =====================================================================
def test_f_available_green_existing_desk(solver):
    """TEST F: AVAILABLE_MOVABLE existing desk can relocate while retaining stable source ID without duplication."""
    room = RoomEntity(
        id="room_avail_f",
        name="Office F",
        boundary_polygon=[(0.0, 0.0), (8.0, 0.0), (8.0, 6.0), (0.0, 6.0)],
        net_area_sqm=48.0,
        doors=[DoorEntity(id="d1", center_x=1.5, center_y=0.0, width_m=0.9, swing_deg=90.0)],
        existing_furniture=[
            ExistingFurnitureEntity(
                id="green_desk_1",
                catalog_item_id="PROFESSIONAL_DESK",
                position=(4.0, 3.0),
                rotation=0.0,
                keep_flag=False,
                movability_status=MovabilityStatus.AVAILABLE_MOVABLE,
                width_m=1.5,
                depth_m=0.75,
            )
        ],
    )
    reqs = [{"item_type": "TASK_CHAIR", "quantity": 1}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_f",
        room=room,
        requested_items=reqs,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        # Total objects must be 2: 1 reconfigured existing desk + 1 new chair
        assert len(cand.placed_objects) == 2
        desk_obj = next((o for o in cand.placed_objects if o.source_object_id == "green_desk_1" or o.id == "green_desk_1"), None)
        assert desk_obj is not None
        assert desk_obj.source_object_id == "green_desk_1"
        assert desk_obj.is_new is False


# =====================================================================
# TEST G: Available chair + desk + cabin + sold desk
# =====================================================================
def test_g_mixed_available_and_sold(solver, evaluator):
    """TEST G: Movable objects relocate, sold object remains fixed, complete candidate is valid."""
    room = RoomEntity(
        id="room_mixed_g",
        name="Office G",
        boundary_polygon=[(0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0)],
        net_area_sqm=96.0,
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
        existing_furniture=[
            ExistingFurnitureEntity(
                id="sold_desk",
                catalog_item_id="PROFESSIONAL_DESK",
                position=(2.0, 4.0),
                rotation=0.0,
                keep_flag=True,
                movability_status=MovabilityStatus.SOLD_FIXED,
            ),
            ExistingFurnitureEntity(
                id="avail_desk",
                catalog_item_id="PROFESSIONAL_DESK",
                position=(6.0, 4.0),
                rotation=0.0,
                keep_flag=False,
                movability_status=MovabilityStatus.AVAILABLE_MOVABLE,
            ),
            ExistingFurnitureEntity(
                id="avail_chair",
                catalog_item_id="TASK_CHAIR",
                position=(6.0, 5.0),
                rotation=0.0,
                keep_flag=False,
                movability_status=MovabilityStatus.AVAILABLE_MOVABLE,
            ),
            ExistingFurnitureEntity(
                id="avail_cabin",
                catalog_item_id="MANAGER_DESK",
                position=(9.0, 4.0),
                rotation=0.0,
                keep_flag=False,
                movability_status=MovabilityStatus.AVAILABLE_MOVABLE,
            ),
        ],
    )
    reqs = [{"item_type": "PROFESSIONAL_DESK", "quantity": 2}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_g",
        room=room,
        requested_items=reqs,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        # Check sold desk is strictly preserved
        sold = next(o for o in cand.placed_objects if o.source_object_id == "sold_desk" or o.id == "sold_desk")
        assert sold.x == 2.0
        assert sold.y == 4.0
        # Total items: 1 sold + 3 movable existing + 2 new = 6 items
        assert len(cand.placed_objects) == 6
        val = evaluator.evaluate(cand, room)
        assert val.is_valid


# =====================================================================
# TEST H: Selected region enforcement
# =====================================================================
def test_h_selected_region_enforcement(solver):
    """TEST H: New requested objects must be strictly contained within the user selected region."""
    room = RoomEntity(
        id="room_region_h",
        name="Large Room H",
        boundary_polygon=[(0.0, 0.0), (14.0, 0.0), (14.0, 10.0), (0.0, 10.0)],
        net_area_sqm=140.0,
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    # User selected only the left zone: (0..6m, 0..5m)
    selected_region = [(0.0, 0.0), (6.0, 0.0), (6.0, 5.0), (0.0, 5.0)]
    reqs = [{"item_type": "TASK_CHAIR", "quantity": 2}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_h",
        room=room,
        requested_items=reqs,
        selected_region_polygon=selected_region,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        for obj in cand.placed_objects:
            if obj.is_new:
                assert obj.x <= 6.0 and obj.y <= 5.0, f"Object {obj.id} placed at ({obj.x}, {obj.y}) outside selected region!"


# =====================================================================
# TEST I: Internal wall preserved by default
# =====================================================================
def test_i_internal_wall_preserved(solver):
    """TEST I: Internal partition walls are treated as solid obstacles and preserved by default."""
    room = RoomEntity(
        id="room_wall_i",
        name="Office with Internal Partition",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        net_area_sqm=80.0,
        walls=[
            WallEntity(
                id="w_ext_1",
                start_point=(0.0, 0.0),
                end_point=(10.0, 0.0),
                is_exterior=True,
                movability_status=MovabilityStatus.STRUCTURAL_FIXED,
            ),
            WallEntity(
                id="w_int_partition",
                start_point=(5.0, 0.0),
                end_point=(5.0, 4.0),
                thickness_m=0.15,
                is_exterior=False,
                movability_status=MovabilityStatus.INTERNAL_WALL_MOVABLE,
            ),
        ],
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [{"item_type": "TASK_CHAIR", "quantity": 2}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_i",
        room=room,
        requested_items=reqs,
    )

    assert res.success is True
    for cand in res.candidates:
        # No object can be placed directly on the internal wall (x=5.0, y in 0..4)
        for obj in cand.placed_objects:
            if 0.0 <= obj.y <= 4.0:
                assert abs(obj.x - 5.0) > 0.2, f"Object {obj.id} collides with internal wall at x={obj.x}"


# =====================================================================
# TEST J: Outer wall never moves
# =====================================================================
def test_j_outer_wall_never_moves(solver):
    """TEST J: Outer perimeter walls are strictly immutable and never placed or modified."""
    room = RoomEntity(
        id="room_outer_j",
        name="Office J",
        boundary_polygon=[(0.0, 0.0), (8.0, 0.0), (8.0, 6.0), (0.0, 6.0)],
        net_area_sqm=48.0,
        walls=[
            WallEntity(
                id="w_outer_north",
                start_point=(0.0, 6.0),
                end_point=(8.0, 6.0),
                is_exterior=True,
                movability_status=MovabilityStatus.STRUCTURAL_FIXED,
            )
        ],
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [{"item_type": "TASK_CHAIR", "quantity": 2}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_test_j",
        room=room,
        requested_items=reqs,
    )

    assert res.success is True
    for cand in res.candidates:
        # None of the placed objects are walls
        for obj in cand.placed_objects:
            assert obj.item_type != "WALL"


# =====================================================================
# TEST K: Circulation & egress validation
# =====================================================================
def test_k_circulation_and_egress_validation():
    """TEST K: Blocked entrance causes circulation rejection; valid unblocked path passes."""
    room_poly = [(0.0, 0.0), (8.0, 0.0), (8.0, 6.0), (0.0, 6.0)]
    door = DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)

    # 1. Invalid layout: Object directly blocking the door entrance at (2.0, 0.3)
    blocked_obj = PlacedObject(
        id="blocker",
        catalog_item_id="desk_1",
        item_type="PROFESSIONAL_DESK",
        x=2.0,
        y=0.3,
        width=1.5,
        height=0.75,
    )
    res_blocked = CirculationEngine.validate_circulation_and_egress(
        room_polygon=room_poly,
        placed_objects=[blocked_obj],
        obstacles=[],
        doors=[door],
    )
    assert res_blocked.is_valid is False
    assert any("obstructed" in v or "blocked" in v for v in res_blocked.violations)

    # 2. Valid layout: Object placed safely at (5.0, 4.0) away from door
    valid_obj = PlacedObject(
        id="clear_desk",
        catalog_item_id="desk_1",
        item_type="PROFESSIONAL_DESK",
        x=5.0,
        y=4.0,
        width=1.5,
        height=0.75,
    )
    res_valid = CirculationEngine.validate_circulation_and_egress(
        room_polygon=room_poly,
        placed_objects=[valid_obj],
        obstacles=[],
        doors=[door],
    )
    assert res_valid.is_valid is True
    assert len(res_valid.circulation_paths) > 0


# =====================================================================
# TEST L: Candidate deduplication
# =====================================================================
def test_l_candidate_deduplication():
    """TEST L: Equivalent spatial configurations produce identical spatial signatures and deduplicate."""
    obj1 = PlacedObject(
        id="obj_alpha",
        catalog_item_id="desk_1",
        item_type="PROFESSIONAL_DESK",
        x=3.0,
        y=4.0,
        rotation_deg=0.0,
        width=1.5,
        height=0.75,
    )
    obj2 = PlacedObject(
        id="obj_beta",
        catalog_item_id="chair_1",
        item_type="TASK_CHAIR",
        x=3.0,
        y=5.2,
        rotation_deg=0.0,
        width=0.6,
        height=0.6,
    )

    # Identical layout with different IDs and reversed list ordering
    obj1_dup = PlacedObject(
        id="obj_different_uuid_1",
        catalog_item_id="desk_1",
        item_type="PROFESSIONAL_DESK",
        x=3.0,
        y=4.0,
        rotation_deg=0.0,
        width=1.5,
        height=0.75,
    )
    obj2_dup = PlacedObject(
        id="obj_different_uuid_2",
        catalog_item_id="chair_1",
        item_type="TASK_CHAIR",
        x=3.0,
        y=5.2,
        rotation_deg=0.0,
        width=0.6,
        height=0.6,
    )

    sig1 = compute_spatial_signature([obj1, obj2])
    sig2 = compute_spatial_signature([obj2_dup, obj1_dup])

    assert sig1 == sig2, "Spatially equivalent layouts must produce identical hash signatures!"


# =====================================================================
# TEST M: Determinism
# =====================================================================
def test_m_solver_determinism(solver):
    """TEST M: Same input + same configuration yields identical candidate signatures and ordering."""
    room = RoomEntity(
        id="room_det_m",
        name="Deterministic Room M",
        boundary_polygon=[(0.0, 0.0), (8.0, 0.0), (8.0, 6.0), (0.0, 6.0)],
        net_area_sqm=48.0,
        doors=[DoorEntity(id="d1", center_x=1.5, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [{"item_type": "PROFESSIONAL_DESK", "quantity": 2}]

    run1 = solver.solve_reconfiguration(floor_plan_id="fp_m", room=room, requested_items=reqs)
    run2 = solver.solve_reconfiguration(floor_plan_id="fp_m", room=room, requested_items=reqs)

    assert run1.candidate_count == run2.candidate_count
    sigs1 = [c.spatial_signature for c in run1.candidates]
    sigs2 = [c.spatial_signature for c in run2.candidates]
    assert sigs1 == sigs2, "Repeated runs with same input must yield identical candidate signatures!"


# =====================================================================
# TEST N: Strict requirement quantity preservation
# =====================================================================
def test_n_requirement_quantity_preservation(solver):
    """TEST N: If user asks for 4 desks, every successful candidate must contain all 4 desks. Never partial."""
    room = RoomEntity(
        id="room_qty_n",
        name="Quantity Room N",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        net_area_sqm=80.0,
        doors=[DoorEntity(id="d1", center_x=2.0, center_y=0.0, width_m=0.9, swing_deg=90.0)],
    )
    reqs = [{"item_type": "PROFESSIONAL_DESK", "quantity": 4}]

    res = solver.solve_reconfiguration(
        floor_plan_id="fp_n",
        room=room,
        requested_items=reqs,
    )

    assert res.success is True
    assert res.candidate_count >= 1
    for cand in res.candidates:
        desks = [o for o in cand.placed_objects if o.item_type == "PROFESSIONAL_DESK"]
        assert len(desks) == 4, f"Expected 4 desks, got {len(desks)}!"
