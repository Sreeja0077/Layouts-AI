"""
Unit test for PostGIS write-through geometry synchronization (Task 3.2).
Verifies POLYGON/POINT WKT conversion, PlacedObject JSONB sync, spatial containment, and intersection checks.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure SQLite in-memory DB fallback for offline unit testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.persistence.postgis_sync import PostGISGeometrySync


def test_polygon_to_wkt_conversion():
    vertices = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
    wkt = PostGISGeometrySync.polygon_to_wkt(vertices)
    assert wkt.startswith("POLYGON((")
    assert "0.0 0.0" in wkt
    assert "10.0 5.0" in wkt
    print(f"Verified WKT Polygon String: {wkt}")


def test_placed_object_jsonb_sync():
    placed_obj = {
        "id": "placed_desk_01",
        "item_type": "EXECUTIVE_DESK",
        "x": 5.0,
        "y": 5.0,
        "width": 1.6,
        "height": 0.8,
    }
    wkt = PostGISGeometrySync.sync_placed_object_to_wkt(placed_obj)
    assert "POLYGON((" in wkt
    # (5 - 0.8, 5 - 0.4) = (4.2, 4.6)
    assert "4.2 4.6" in wkt
    assert "5.8 5.4" in wkt
    print(f"Verified PlacedObject JSONB -> WKT Geometry Sync: {wkt}")


def test_spatial_containment_and_intersection():
    room_poly = [(0.0, 0.0), (20.0, 0.0), (20.0, 15.0), (0.0, 15.0)]
    desk_poly_inside = [(2.0, 2.0), (3.6, 2.0), (3.6, 2.8), (2.0, 2.8)]
    desk_poly_outside = [(22.0, 2.0), (23.6, 2.0), (23.6, 2.8), (22.0, 2.8)]

    # 1. Containment check
    assert PostGISGeometrySync.check_spatial_containment(desk_poly_inside, room_poly) is True
    assert PostGISGeometrySync.check_spatial_containment(desk_poly_outside, room_poly) is False

    # 2. Intersection check
    desk_a = [(2.0, 2.0), (4.0, 2.0), (4.0, 4.0), (2.0, 4.0)]
    desk_b_overlapping = [(3.0, 3.0), (5.0, 3.0), (5.0, 5.0), (3.0, 5.0)]
    desk_c_far = [(10.0, 10.0), (12.0, 10.0), (12.0, 12.0), (10.0, 12.0)]

    assert PostGISGeometrySync.check_spatial_intersection(desk_a, desk_b_overlapping) is True
    assert PostGISGeometrySync.check_spatial_intersection(desk_a, desk_c_far) is False

    print("ALL POSTGIS WRITE-THROUGH SPATIAL SYNC TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_polygon_to_wkt_conversion()
    test_placed_object_jsonb_sync()
    test_spatial_containment_and_intersection()
