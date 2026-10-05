"""
Comprehensive Unit Test Suite for Authoritative Free-Space Geometry Engine (Task 4.1).
Verifies Shapely/GEOS subtraction, hole preservation, MultiPolygon handling,
wall perimeter insets, obstacle clearance buffers, concave rooms, point containment,
and explicit error handling when Shapely is missing.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import patch

# Ensure workspace root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from shapely.geometry import Point, Polygon, MultiPolygon
from app.domain.geometry.entities import DoorEntity
from geometry.geo_engine.freespace import FreeSpaceEngine


def test_1_rectangular_room_no_obstacles():
    """10m x 10m rectangular room with 0.0 inset and no obstacles -> 100.0 sqm."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[], wall_inset_buffer=0.0)

    assert isinstance(geom, Polygon)
    assert not geom.is_empty
    assert abs(geom.area - 100.0) < 1e-4

    res_dict = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[], wall_inset_buffer=0.0)
    assert res_dict["type"] == "Polygon"
    assert res_dict["area_sqm"] == 100.0
    assert not res_dict["is_empty"]


def test_2_perimeter_wall_inset():
    """10m x 10m room with 0.5m wall inset -> 9m x 9m = 81.0 sqm."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[], wall_inset_buffer=0.5)

    assert isinstance(geom, Polygon)
    assert abs(geom.area - 81.0) < 1e-4

    res_dict = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[], wall_inset_buffer=0.5)
    assert res_dict["area_sqm"] == 81.0


def test_3_central_column_subtraction():
    """10m x 10m room (100 sqm) minus 2m x 2m central column (4 sqm) -> 96.0 sqm."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    column = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[column], wall_inset_buffer=0.0)
    assert abs(geom.area - 96.0) < 1e-4


def test_4_central_column_hole_preservation():
    """Verify central obstacle creates a Polygon with 1 interior hole and point containment is accurate."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    column = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[column], wall_inset_buffer=0.0)

    assert geom.geom_type == "Polygon"
    assert len(geom.interiors) == 1  # 1 interior hole ring
    assert abs(geom.area - 96.0) < 1e-4

    # Point inside the central column must NOT be contained in free-space
    assert not geom.contains(Point(5.0, 5.0))

    # Point in usable room space IS contained
    assert geom.contains(Point(2.0, 2.0))

    # GeoJSON serialization must preserve the interior ring
    res_dict = FreeSpaceEngine.serialize_geometry(geom)
    assert res_dict["type"] == "Polygon"
    assert len(res_dict["coordinates"]) == 2  # Outer ring + 1 hole ring
    assert res_dict["area_sqm"] == 96.0


def test_5_multiple_obstacles():
    """10m x 10m room minus two 1m x 1m columns -> 98.0 sqm and 2 interior holes."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    col1 = [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0)]
    col2 = [(7.0, 7.0), (8.0, 7.0), (8.0, 8.0), (7.0, 8.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[col1, col2])
    assert geom.geom_type == "Polygon"
    assert len(geom.interiors) == 2
    assert abs(geom.area - 98.0) < 1e-4


def test_6_obstacle_outside_room():
    """Obstacle entirely outside room does not reduce free-space area."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    outside_col = [(15.0, 15.0), (16.0, 15.0), (16.0, 16.0), (15.0, 16.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[outside_col])
    assert abs(geom.area - 100.0) < 1e-4
    assert len(geom.interiors) == 0


def test_7_obstacle_crossing_boundary():
    """Obstacle straddling the room boundary only subtracts its overlapping portion inside the room."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    straddle_col = [(8.0, 4.0), (12.0, 4.0), (12.0, 6.0), (8.0, 6.0)]  # 4m x 2m column, 2m x 2m inside room

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[straddle_col])
    assert abs(geom.area - 96.0) < 1e-4


def test_8_obstacle_touching_boundary():
    """Obstacle flush against room boundary subtracts cleanly without topology errors."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    touching_col = [(0.0, 4.0), (2.0, 4.0), (2.0, 6.0), (0.0, 6.0)]  # 2m x 2m against x=0 wall

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[touching_col])
    assert geom.is_valid
    assert abs(geom.area - 96.0) < 1e-4


def test_9_concave_l_shaped_room():
    """L-shaped concave room (75.0 sqm) with wall inset and column subtraction."""
    l_room = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)]
    col = [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0)]

    geom_raw = FreeSpaceEngine.compute_usable_geometry(l_room, obstacles=[])
    assert abs(geom_raw.area - 75.0) < 1e-4

    geom_sub = FreeSpaceEngine.compute_usable_geometry(l_room, obstacles=[col])
    assert abs(geom_sub.area - 74.0) < 1e-4

    geom_inset = FreeSpaceEngine.compute_usable_geometry(l_room, obstacles=[], wall_inset_buffer=0.5)
    assert geom_inset.is_valid
    assert geom_inset.area < 75.0


def test_10_u_shaped_room():
    """U-shaped concave room geometry subtraction."""
    u_room = [(0.0, 0.0), (9.0, 0.0), (9.0, 9.0), (6.0, 9.0), (6.0, 3.0), (3.0, 3.0), (3.0, 9.0), (0.0, 9.0)]
    geom = FreeSpaceEngine.compute_usable_geometry(u_room, obstacles=[])
    assert geom.is_valid
    assert abs(geom.area - 63.0) < 1e-4


def test_11_obstacle_creating_multipolygon():
    """Full-height barrier obstacle splits 20m x 10m room into 2 disconnected MultiPolygon components."""
    room_poly = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    barrier = [(9.5, 0.0), (10.5, 0.0), (10.5, 10.0), (9.5, 10.0)]  # 1m wide barrier spanning y=0 to y=10

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[barrier])
    assert geom.geom_type == "MultiPolygon"
    assert len(geom.geoms) == 2  # 2 distinct polygon components
    assert abs(geom.area - 190.0) < 1e-4

    res_dict = FreeSpaceEngine.serialize_geometry(geom)
    assert res_dict["type"] == "MultiPolygon"
    assert len(res_dict["coordinates"]) == 2
    assert res_dict["area_sqm"] == 190.0


def test_12_full_obstruction_returns_empty_result():
    """Obstacle covering the entire room returns an empty geometry."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    giant_obs = [(-1.0, -1.0), (11.0, -1.0), (11.0, 11.0), (-1.0, 11.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[giant_obs])
    assert geom.is_empty
    assert geom.area == 0.0

    res_dict = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[giant_obs])
    assert res_dict["is_empty"] is True
    assert res_dict["area_sqm"] == 0.0
    assert res_dict["coordinates"] == []


def test_13_obstacle_clearance_buffer():
    """Obstacle clearance buffer expands 1m x 1m column (with 0.5m rounded corner buffer) before subtraction."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    small_col = [(4.5, 4.5), (5.5, 4.5), (5.5, 5.5), (4.5, 5.5)]  # 1m x 1m center column

    # 0.5m clearance buffer around 1m x 1m column subtracts 3.784 sqm (leaving 96.216 sqm)
    geom = FreeSpaceEngine.compute_usable_geometry(
        room_poly, obstacles=[small_col], obstacle_clearance_buffer=0.5
    )
    assert abs(geom.area - 96.216) < 1e-2


def test_14_door_swing_arc_subtraction():
    """Door swing arc polygon generated by DoorEntity is subtracted cleanly from room free-space."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    door = DoorEntity(id="d1", center_x=5.0, center_y=0.0, width_m=1.0, swing_deg=90.0)
    swing_polygon = door.get_swing_arc_polygon()

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[swing_polygon])
    assert geom.is_valid
    assert geom.area < 100.0
    assert geom.area > 98.0  # ~0.785 sqm arc subtracted


def test_15_invalid_room_geometry_handling():
    """Self-intersecting bow-tie room polygon is repaired via make_valid() into valid geometry."""
    bowtie_room = [(0.0, 0.0), (10.0, 10.0), (10.0, 0.0), (0.0, 10.0)]
    geom = FreeSpaceEngine.compute_usable_geometry(bowtie_room, obstacles=[])
    assert geom.is_valid
    assert not geom.is_empty


def test_16_invalid_obstacle_geometry_handling():
    """Self-intersecting obstacle polygon is repaired via make_valid() and subtracted cleanly."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    bowtie_obs = [(4.0, 4.0), (6.0, 6.0), (6.0, 4.0), (4.0, 6.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[bowtie_obs])
    assert geom.is_valid
    assert geom.area < 100.0


def test_17_polygon_area_with_holes():
    """calculate_freespace_area subtracts interior hole areas automatically."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    col1 = [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0)]  # 1 sqm
    col2 = [(7.0, 7.0), (8.0, 7.0), (8.0, 8.0), (7.0, 8.0)]  # 1 sqm

    res_dict = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[col1, col2])
    area = FreeSpaceEngine.calculate_freespace_area(res_dict)
    assert abs(area - 98.0) < 1e-4


def test_18_multipolygon_total_area():
    """calculate_freespace_area computes total combined area for MultiPolygons."""
    room_poly = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    barrier = [(9.5, 0.0), (10.5, 0.0), (10.5, 10.0), (9.5, 10.0)]

    res_dict = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[barrier])
    area = FreeSpaceEngine.calculate_freespace_area(res_dict)
    assert abs(area - 190.0) < 1e-4


def test_19_point_containment_regression_for_hole():
    """Verify Point(x,y) inside column returns False while Point(x,y) inside room returns True."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    column = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

    geom = FreeSpaceEngine.compute_usable_geometry(room_poly, obstacles=[column])
    assert geom.contains(Point(1.0, 1.0)) is True
    assert geom.contains(Point(5.0, 5.0)) is False


def test_20_deterministic_repeated_execution():
    """Verify 100 repeated executions yield identical area and GeoJSON results."""
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    column = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

    baseline = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[column], wall_inset_buffer=0.2)
    for _ in range(100):
        current = FreeSpaceEngine.compute_usable_freespace(room_poly, obstacles=[column], wall_inset_buffer=0.2)
        assert current["area_sqm"] == baseline["area_sqm"]
        assert current["coordinates"] == baseline["coordinates"]


def test_21_explicit_failure_when_shapely_unavailable():
    """Verify ImportError is raised explicitly if HAS_SHAPELY is False (zero fake fallbacks)."""
    with patch("geometry.geo_engine.freespace.HAS_SHAPELY", False):
        with pytest.raises(ImportError) as exc_info:
            FreeSpaceEngine.compute_usable_geometry([(0, 0), (10, 0), (10, 10)])
        assert "Shapely/GEOS is required" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
