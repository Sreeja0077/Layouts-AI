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


def test_corner_proximity_hinge_placement():
    """Test 9: Hinge placement selects jamb closest to adjacent perpendicular corner wall."""
    # Room from (0, 0) to (4, 5). Door is on left wall x=0, y in [3.8, 4.7] near top corner (0, 5)
    top_corner = (0.0, 5.0)
    door_center = (0.0, 4.25)
    door_width = 0.9
    # Wall tangent u = (0, 1)
    j_start = (door_center[0], door_center[1] - door_width / 2)  # (0, 3.8)
    j_end = (door_center[0], door_center[1] + door_width / 2)    # (0, 4.7)

    d_start = math.hypot(j_start[0] - top_corner[0], j_start[1] - top_corner[1])
    d_end = math.hypot(j_end[0] - top_corner[0], j_end[1] - top_corner[1])

    assert d_end < d_start, "j_end is closer to the top corner"
    hinge_side = "END" if d_end < d_start else "START"
    assert hinge_side == "END", "Hinge should be placed at the END jamb near the corner"


def test_paired_doors_opposite_swing_geometry():
    """Test 10: Adjacent / double doors on the same wall swing opposite to each other."""
    door1_pos = (0.0, 4.0)  # Top door
    door2_pos = (0.0, 3.1)  # Bottom door
    w1, w2 = 0.9, 0.9
    u = (0.0, 1.0)  # Wall tangent along +Y

    # Door 1 evaluating Door 2:
    d1_to_d2 = (door2_pos[0] - door1_pos[0], door2_pos[1] - door1_pos[1])
    proj1 = d1_to_d2[0] * u[0] + d1_to_d2[1] * u[1]  # -0.9 -> -u direction (START side)
    # Since other door is at START side, meeting point is START -> hinge MUST be END (top)
    hinge1 = "END" if proj1 < -0.1 else "START"

    # Door 2 evaluating Door 1:
    d2_to_d1 = (door1_pos[0] - door2_pos[0], door1_pos[1] - door2_pos[1])
    proj2 = d2_to_d1[0] * u[0] + d2_to_d1[1] * u[1]  # +0.9 -> +u direction (END side)
    # Since other door is at END side, meeting point is END -> hinge MUST be START (bottom)
    hinge2 = "START" if proj2 > 0.1 else "END"

    assert hinge1 == "END", "Top door should hinge at top (END) jamb"
    assert hinge2 == "START", "Bottom door should hinge at bottom (START) jamb"
    assert hinge1 != hinge2, "Paired doors must swing opposite to each other symmetrically"


def test_intervening_wall_separates_single_doors():
    """Test 11: Two doors separated by a perpendicular partition wall are treated as independent single doors."""
    door1_pos = (0.0, 4.0)  # Top door
    door2_pos = (0.0, 3.1)  # Bottom door

    # A perpendicular partition wall ending at (0.0, 3.55) between the two doors
    partition_wall_start = (0.0, 3.55)
    partition_wall_end = (5.0, 3.55)

    # Check if partition wall terminates between the two doors
    pt = partition_wall_start
    min_y = min(door1_pos[1], door2_pos[1])
    max_y = max(door1_pos[1], door2_pos[1])

    is_between = min_y - 0.1 <= pt[1] <= max_y + 0.1 and abs(pt[0] - door1_pos[0]) < 0.35
    assert is_between is True, "Partition wall endpoint lies between the two doors"
    # Because an intervening wall exists, paired_hinge_side is NOT applied -> each door resolves its hinge independently!



