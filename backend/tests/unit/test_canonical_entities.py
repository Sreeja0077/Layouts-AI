"""
Comprehensive Unit Test Suite for Canonical Architectural BIM Entity Models (Task 3.1).
Verifies model construction, geometric calculations, relationship consistency,
keep_flag semantics, JSON serialization, and negative validation cases.
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.geometry.entities import (
    BeamEntity,
    CanonicalFloorPlan,
    ColumnEntity,
    DoorEntity,
    EntityType,
    ExistingFurnitureEntity,
    RoomEntity,
    WallEntity,
    WindowEntity,
)


def test_wall_entity_construction_and_validation():
    """Verify WallEntity valid construction, metric dimensions, and negative thickness rejection."""
    wall = WallEntity(
        id="wall_001",
        start_point=(0.0, 0.0),
        end_point=(10.0, 0.0),
        thickness_m=0.20,
        is_exterior=True,
    )
    assert wall.id == "wall_001"
    assert wall.start_point == (0.0, 0.0)
    assert wall.end_point == (10.0, 0.0)
    assert wall.thickness_m == 0.20
    assert wall.is_exterior is True

    # Negative thickness_m must be rejected
    with pytest.raises(ValidationError):
        WallEntity(
            id="wall_invalid",
            start_point=(0.0, 0.0),
            end_point=(5.0, 0.0),
            thickness_m=-0.15,
        )

    # Zero thickness_m must be rejected (gt=0.0)
    with pytest.raises(ValidationError):
        WallEntity(
            id="wall_zero",
            start_point=(0.0, 0.0),
            end_point=(5.0, 0.0),
            thickness_m=0.0,
        )


def test_door_entity_construction_swing_arc_and_validation():
    """Verify DoorEntity valid construction, swing arc calculation, and invalid width rejection."""
    door = DoorEntity(
        id="door_001",
        center_x=10.0,
        center_y=5.0,
        width_m=0.9,
        swing_deg=90.0,
        swing_direction="INSIDE_LEFT",
    )
    assert door.id == "door_001"
    assert door.width_m == 0.9
    assert door.swing_deg == 90.0
    assert door.swing_direction == "INSIDE_LEFT"

    polygon = door.get_swing_arc_polygon(steps=8)
    assert len(polygon) == 10  # Pivot point + 9 steps
    assert polygon[0] == (10.0, 5.0)

    # Negative width must be rejected
    with pytest.raises(ValidationError):
        DoorEntity(id="door_inv", center_x=0.0, center_y=0.0, width_m=-0.9)


def test_window_entity_construction_and_validation():
    """Verify WindowEntity width, sill height, and negative bound checks."""
    window = WindowEntity(
        id="win_001",
        wall_id="wall_001",
        start_point=(2.0, 0.0),
        end_point=(4.0, 0.0),
        width_m=2.0,
        sill_height_m=0.9,
    )
    assert window.id == "win_001"
    assert window.width_m == 2.0
    assert window.sill_height_m == 0.9

    # Negative sill height must be rejected
    with pytest.raises(ValidationError):
        WindowEntity(
            id="win_inv",
            start_point=(0.0, 0.0),
            end_point=(2.0, 0.0),
            width_m=2.0,
            sill_height_m=-0.5,
        )


def test_column_entity_construction_and_obstacle_polygon():
    """Verify ColumnEntity obstacle polygon calculation including clearance buffer."""
    col = ColumnEntity(
        id="col_001",
        center_x=4.0,
        center_y=4.0,
        width_m=0.6,
        height_m=0.6,
        clearance_buffer_m=0.2,
    )
    assert col.id == "col_001"
    bbox = col.get_obstacle_polygon()
    assert len(bbox) == 4
    assert bbox[0] == (3.5, 3.5)
    assert bbox[2] == (4.5, 4.5)

    # Negative clearance buffer must be rejected
    with pytest.raises(ValidationError):
        ColumnEntity(id="col_inv", center_x=0.0, center_y=0.0, clearance_buffer_m=-0.1)


def test_beam_entity_construction():
    """Verify BeamEntity construction and clearance height."""
    beam = BeamEntity(
        id="beam_001",
        start_point=(0.0, 0.0),
        end_point=(10.0, 0.0),
        clearance_height_m=2.8,
    )
    assert beam.id == "beam_001"
    assert beam.clearance_height_m == 2.8


def test_existing_furniture_entity_semantics_and_validation():
    """Verify ExistingFurnitureEntity keep_flag semantics, required fields, and extra forbid check."""
    # Retained furniture (keep_flag=True)
    f_retained = ExistingFurnitureEntity(
        id="furn_001",
        catalog_item_id="reception_desk_01",
        position=(5.0, 2.5),
        rotation=45.0,
        keep_flag=True,
    )
    assert f_retained.id == "furn_001"
    assert f_retained.catalog_item_id == "reception_desk_01"
    assert f_retained.position == (5.0, 2.5)
    assert f_retained.rotation == 45.0
    assert f_retained.keep_flag is True

    # Movable furniture (keep_flag=False)
    f_movable = ExistingFurnitureEntity(
        id="furn_002",
        catalog_item_id="temp_chair_02",
        position=(1.0, 1.0),
        rotation=0.0,
        keep_flag=False,
    )
    assert f_movable.keep_flag is False

    # Missing catalog_item_id must be rejected
    with pytest.raises(ValidationError):
        ExistingFurnitureEntity(
            id="furn_inv",
            position=(0.0, 0.0),
        )

    # Malformed position tuple must be rejected
    with pytest.raises(ValidationError):
        ExistingFurnitureEntity(
            id="furn_inv",
            catalog_item_id="desk_01",
            position=(1.0,),  # Needs 2 elements
        )

    # Extra unexpected fields must be rejected due to extra="forbid"
    with pytest.raises(ValidationError):
        ExistingFurnitureEntity(
            id="furn_extra",
            catalog_item_id="desk_01",
            position=(0.0, 0.0),
            confidence_score=0.99,  # Unsanctioned extra field
        )


def test_room_entity_relationships_and_validation():
    """Verify RoomEntity boundary, net area, related entity IDs, nested entities, and relationship consistency."""
    door = DoorEntity(id="d1", center_x=5.0, center_y=0.0, width_m=0.9)
    window = WindowEntity(id="w1", start_point=(2.0, 0.0), end_point=(4.0, 0.0), width_m=2.0)
    col = ColumnEntity(id="c1", center_x=3.0, center_y=3.0)
    furn = ExistingFurnitureEntity(id="f1", catalog_item_id="desk_01", position=(4.0, 4.0), keep_flag=True)

    room = RoomEntity(
        id="room_101",
        name="Executive Conference Room",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        net_area_sqm=80.0,
        wall_ids=["wall_1"],
        door_ids=["d1"],
        window_ids=["w1"],
        column_ids=["c1"],
        existing_furniture_ids=["f1"],
        doors=[door],
        windows=[window],
        columns=[col],
        existing_furniture=[furn],
    )
    assert room.id == "room_101"
    assert room.net_area_sqm == 80.0
    assert room.existing_furniture_ids == ["f1"]
    assert len(room.existing_furniture) == 1
    assert room.existing_furniture[0].catalog_item_id == "desk_01"

    # Negative area must be rejected
    with pytest.raises(ValidationError):
        RoomEntity(
            id="room_inv",
            name="Invalid Room",
            boundary_polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
            net_area_sqm=-10.0,
        )


def test_canonical_floor_plan_aggregation():
    """Verify CanonicalFloorPlan aggregate holds all physical core entities and revision metadata."""
    wall = WallEntity(id="w1", start_point=(0.0, 0.0), end_point=(10.0, 0.0), thickness_m=0.15)
    door = DoorEntity(id="d1", center_x=5.0, center_y=0.0)
    window = WindowEntity(id="win1", start_point=(2.0, 0.0), end_point=(4.0, 0.0), width_m=2.0)
    column = ColumnEntity(id="c1", center_x=2.0, center_y=2.0)
    beam = BeamEntity(id="b1", start_point=(0.0, 5.0), end_point=(10.0, 5.0))
    furniture = ExistingFurnitureEntity(id="f1", catalog_item_id="reception_desk", position=(5.0, 5.0), keep_flag=True)

    room = RoomEntity(
        id="room_101",
        name="Lobby",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        net_area_sqm=100.0,
        wall_ids=["w1"],
        door_ids=["d1"],
        window_ids=["win1"],
        column_ids=["c1"],
        existing_furniture_ids=["f1"],
        doors=[door],
        windows=[window],
        columns=[column],
        existing_furniture=[furniture],
    )

    floor_plan = CanonicalFloorPlan(
        id="fp_101",
        name="Level 4 Canonical Plan",
        source_version_id="ver_001",
        project_id="proj_alpha",
        current_published_revision_id="rev_pub_01",
        current_working_revision_id="rev_work_02",
        rooms=[room],
        walls=[wall],
        doors=[door],
        windows=[window],
        columns=[column],
        beams=[beam],
        existing_furniture=[furniture],
    )

    assert len(floor_plan.rooms) == 1
    assert len(floor_plan.walls) == 1
    assert len(floor_plan.doors) == 1
    assert len(floor_plan.windows) == 1
    assert len(floor_plan.columns) == 1
    assert len(floor_plan.beams) == 1
    assert len(floor_plan.existing_furniture) == 1
    assert floor_plan.existing_furniture[0].catalog_item_id == "reception_desk"
    assert floor_plan.project_id == "proj_alpha"


def test_pydantic_v2_json_serialization():
    """Verify clean Pydantic v2 JSON/dict roundtrip serialization for canonical models."""
    furn = ExistingFurnitureEntity(
        id="furn_99",
        catalog_item_id="executive_desk",
        position=(12.5, 8.2),
        rotation=90.0,
        keep_flag=True,
    )
    floor_plan = CanonicalFloorPlan(
        id="fp_serial",
        name="Serialization Test Plan",
        existing_furniture=[furn],
    )

    json_data = floor_plan.model_dump_json()
    deserialized = CanonicalFloorPlan.model_validate_json(json_data)

    assert deserialized.id == floor_plan.id
    assert len(deserialized.existing_furniture) == 1
    assert deserialized.existing_furniture[0].id == "furn_99"
    assert deserialized.existing_furniture[0].position == (12.5, 8.2)
    assert deserialized.existing_furniture[0].keep_flag is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
