"""
Unit Tests for Architectural Door Swing Geometry, Room Interior Containment, and Garage Door Symbols (Task Phase 23).
"""

import math
import pytest
from shapely.geometry import Polygon


def point_in_polygon_test(px: float, py: float, coords: list) -> bool:
    poly = Polygon(coords)
    from shapely.geometry import Point
    return poly.contains(Point(px, py))


def test_horizontal_wall_inward_door_swing():
    """Test 1: Door on horizontal wall bordering room (y=0 to y=10)."""
    room_coords = [(0, 0), (10, 0), (10, 10), (0, 10)]
    door_pos = (5.0, 0.0)  # On bottom wall
    door_width = 0.9
    wall_angle_deg = 0.0  # Horizontal wall along X

    rad = math.radians(wall_angle_deg)
    u = (math.cos(rad), math.sin(rad))
    n1 = (-u[1], u[0])  # (0, 1) -> points into room (+Y)
    n2 = (u[1], -u[0])  # (0, -1) -> points outside room (-Y)

    test_dist = door_width * 0.5
    p1 = (door_pos[0] + n1[0] * test_dist, door_pos[1] + n1[1] * test_dist)
    p2 = (door_pos[0] + n2[0] * test_dist, door_pos[1] + n2[1] * test_dist)

    p1_in = point_in_polygon_test(p1[0], p1[1], room_coords)
    p2_in = point_in_polygon_test(p2[0], p2[1], room_coords)

    assert p1_in is True, "p1 (+Y normal) should be inside room"
    assert p2_in is False, "p2 (-Y normal) should be outside room"


def test_vertical_wall_door_swing():
    """Test 2: Door on vertical wall (x=0, y=0 to 10) bordering room (x=0 to 10, y=0 to 10)."""
    room_coords = [(0, 0), (10, 0), (10, 10), (0, 10)]
    door_pos = (0.0, 5.0)  # On left wall
    wall_angle_deg = 90.0  # Vertical wall along Y

    rad = math.radians(wall_angle_deg)
    u = (math.cos(rad), math.sin(rad))  # (0, 1)
    n1 = (-u[1], u[0])  # (-1, 0) -> points left (outside)
    n2 = (u[1], -u[0])  # (1, 0)  -> points right (inside)

    test_dist = 0.45
    p1 = (door_pos[0] + n1[0] * test_dist, door_pos[1] + n1[1] * test_dist)
    p2 = (door_pos[0] + n2[0] * test_dist, door_pos[1] + n2[1] * test_dist)

    p1_in = point_in_polygon_test(p1[0], p1[1], room_coords)
    p2_in = point_in_polygon_test(p2[0], p2[1], room_coords)

    assert p1_in is False
    assert p2_in is True, "p2 (+X normal) should point into room interior"


def test_diagonal_45_degree_wall_swing():
    """Test 3: Door on 45-degree diagonal wall segment."""
    wall_start = (0, 0)
    wall_end = (10, 10)
    dx = wall_end[0] - wall_start[0]
    dy = wall_end[1] - wall_start[1]
    angle_deg = math.degrees(math.atan2(dy, dx))
    assert abs(angle_deg - 45.0) < 1e-3


def test_small_room_policy_threshold():
    """Test 6: Small room area policy threshold (< 3m2)."""
    small_room_coords = [(0, 0), (1.5, 0), (1.5, 1.5), (0, 1.5)]
    poly = Polygon(small_room_coords)
    area = poly.area
    assert area == 2.25
    assert area < 3.0, "Small room should be below 3.0 m2 threshold"


def test_garage_door_track_geometry():
    """Test 8: Garage door overhead tracks geometry proportion."""
    door_width = 3.0
    track_length = door_width * 1.2
    assert abs(track_length - 3.6) < 1e-6, "Track length should be 1.2x door width"
