"""
PostGIS Write-Through Geometry Synchronization Engine.
Converts JSONB object records into PostGIS WKT (Well-Known Text) geometry strings
and performs spatial containment & intersection verification.
"""

from typing import Any, Dict, List, Tuple


class PostGISGeometrySync:
    """Synchronizer converting JSONB spatial data into PostGIS WKT geometries."""

    @staticmethod
    def polygon_to_wkt(vertices: List[Tuple[float, float]]) -> str:
        """Convert list of 2D coordinates [(x0, y0), (x1, y1)...] to PostGIS POLYGON WKT string."""
        if not vertices:
            raise ValueError("Vertices list cannot be empty for POLYGON WKT conversion")

        # Ensure polygon ring is closed
        closed_ring = list(vertices)
        if closed_ring[0] != closed_ring[-1]:
            closed_ring.append(closed_ring[0])

        coords_str = ", ".join([f"{x} {y}" for x, y in closed_ring])
        return f"POLYGON(({coords_str}))"

    @staticmethod
    def point_to_wkt(x: float, y: float) -> str:
        """Convert 2D point (x, y) to PostGIS POINT WKT string."""
        return f"POINT({x} {y})"

    @staticmethod
    def sync_placed_object_to_wkt(placed_object_json: Dict[str, Any]) -> str:
        """
        Extract coordinates from PlacedObject JSONB record and generate PostGIS POLYGON WKT string.
        Calculates rotated bounding box coordinates.
        """
        x = float(placed_object_json.get("x", 0.0))
        y = float(placed_object_json.get("y", 0.0))
        width = float(placed_object_json.get("width", 1.0))
        height = float(placed_object_json.get("height", 1.0))

        hw, hh = width / 2.0, height / 2.0
        vertices = [
            (round(x - hw, 3), round(y - hh, 3)),
            (round(x + hw, 3), round(y - hh, 3)),
            (round(x + hw, 3), round(y + hh, 3)),
            (round(x - hw, 3), round(y + hh, 3)),
        ]
        return PostGISGeometrySync.polygon_to_wkt(vertices)

    @staticmethod
    def check_spatial_containment(
        inner_polygon: List[Tuple[float, float]], outer_polygon: List[Tuple[float, float]]
    ) -> bool:
        """Verify if all vertices of inner polygon reside within outer polygon bounding box."""
        min_x = min(p[0] for p in outer_polygon)
        max_x = max(p[0] for p in outer_polygon)
        min_y = min(p[1] for p in outer_polygon)
        max_y = max(p[1] for p in outer_polygon)

        for px, py in inner_polygon:
            if not (min_x <= px <= max_x and min_y <= py <= max_y):
                return False
        return True

    @staticmethod
    def check_spatial_intersection(
        poly_a: List[Tuple[float, float]], poly_b: List[Tuple[float, float]]
    ) -> bool:
        """Check if two 2D bounding boxes overlap/intersect."""
        min_xa, max_xa = min(p[0] for p in poly_a), max(p[0] for p in poly_a)
        min_ya, max_ya = min(p[1] for p in poly_a), max(p[1] for p in poly_a)

        min_xb, max_xb = min(p[0] for p in poly_b), max(p[0] for p in poly_b)
        min_yb, max_yb = min(p[1] for p in poly_b), max(p[1] for p in poly_b)

        return not (max_xa <= min_xb or min_xa >= max_xb or max_ya <= min_yb or min_ya >= max_yb)
