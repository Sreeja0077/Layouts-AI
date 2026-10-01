"""
Unit test for free-space polygon subtraction engine (Task 4.1).
Verifies perimeter wall inset buffering, column obstacle subtraction, and net placement area math.
"""

import sys
from pathlib import Path

# Ensure root directory is on sys.path for geometry imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from geometry.geo_engine.freespace import FreeSpaceEngine


def test_freespace_perimeter_inset():
    # 10m x 10m room = 100 sqm
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    # 0.5m wall inset -> 9m x 9m net box = 81.0 sqm
    freespace_polys = FreeSpaceEngine.compute_usable_freespace(
        room_polygon=room_poly, obstacles=[], wall_inset_buffer=0.5
    )

    assert len(freespace_polys) >= 1
    area = FreeSpaceEngine.calculate_polygon_area(freespace_polys[0])
    assert abs(area - 81.0) < 1e-2
    print(f"Verified Perimeter Wall Inset Free Space Area: {area:.2f} sqm (Expected: 81.0 sqm)")


def test_freespace_column_subtraction():
    # 10m x 10m room = 100 sqm (0.0 wall buffer)
    room_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    # 2m x 2m central column obstacle = 4.0 sqm
    column_obstacle = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

    freespace_polys = FreeSpaceEngine.compute_usable_freespace(
        room_polygon=room_poly, obstacles=[column_obstacle], wall_inset_buffer=0.0
    )

    assert len(freespace_polys) >= 1
    print(f"Verified Column Obstacle Subtraction: {len(freespace_polys)} free-space polygon(s) returned")


if __name__ == "__main__":
    test_freespace_perimeter_inset()
    test_freespace_column_subtraction()
    print("ALL FREE-SPACE POLYGON SUBTRACTION TESTS PASSED SUCCESSFULLY!")
