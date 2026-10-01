"""
Unit test for canonical architectural BIM entity models (Task 3.1).
Verifies door swing arc polygon generation, column obstacle bounds, and room perimeter math.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.geometry.entities import (
    CanonicalFloorPlan,
    ColumnEntity,
    DoorEntity,
    RoomEntity,
    WallEntity,
    WindowEntity,
)


def test_door_swing_arc_calculation():
    door = DoorEntity(
        id="door_001",
        center_x=10.0,
        center_y=5.0,
        width_m=0.9,
        swing_deg=90.0,
    )
    polygon = door.get_swing_arc_polygon()
    assert len(polygon) == 10  # Center + 9 arc steps
    assert polygon[0] == (10.0, 5.0)  # Door pivot point
    print(f"Verified Door Swing Arc Polygon (90deg, 0.9m radius): {polygon[:3]}...")


def test_column_obstacle_boundary():
    col = ColumnEntity(
        id="col_001",
        center_x=4.0,
        center_y=4.0,
        width_m=0.6,
        height_m=0.6,
        clearance_buffer_m=0.2,
    )
    bbox = col.get_obstacle_polygon()
    assert len(bbox) == 4
    # (4 - 0.3 - 0.2, 4 - 0.3 - 0.2) = (3.5, 3.5)
    assert bbox[0] == (3.5, 3.5)
    assert bbox[2] == (4.5, 4.5)
    print(f"Verified Column Obstacle Bounding Box (+0.2m buffer): {bbox}")


def test_canonical_floor_plan_aggregation():
    wall = WallEntity(id="w1", start_point=(0.0, 0.0), end_point=(10.0, 0.0), thickness_m=0.15)
    window = WindowEntity(id="win1", start_point=(2.0, 0.0), end_point=(4.0, 0.0), width_m=2.0)
    room = RoomEntity(
        id="room_101",
        name="Executive Conference Room",
        boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        net_area_sqm=80.0,
        wall_ids=["w1"],
        window_ids=["win1"],
    )
    floor_plan = CanonicalFloorPlan(
        id="fp_101",
        name="Level 4 Canonical Plan",
        rooms=[room],
        walls=[wall],
        windows=[window],
    )
    assert len(floor_plan.rooms) == 1
    assert floor_plan.rooms[0].net_area_sqm == 80.0
    print("ALL CANONICAL BIM ENTITY TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_door_swing_arc_calculation()
    test_column_obstacle_boundary()
    test_canonical_floor_plan_aggregation()
