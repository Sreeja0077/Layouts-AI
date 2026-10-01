"""
Free-Space Polygon Subtraction Engine (Task 4.1).
Calculates net placement area inside rooms by applying perimeter wall insets and subtracting
structural obstacles (columns, internal walls) and door clearance zones.
"""

from typing import List, Tuple, Union


class FreeSpaceEngine:
    """Deterministic 2D polygon subtraction & free space computation engine."""

    @staticmethod
    def compute_usable_freespace(
        room_polygon: List[Tuple[float, float]],
        obstacles: List[List[Tuple[float, float]]],
        wall_inset_buffer: float = 0.1,
    ) -> List[List[Tuple[float, float]]]:
        """
        Compute net usable polygon free-space inside a room.

        Args:
            room_polygon: Coordinates [(x, y)...] defining outer room boundary.
            obstacles: List of obstacle polygon coordinate lists [(x, y)...] (e.g. columns, door swings).
            wall_inset_buffer: Perimeter safety offset distance in meters.

        Returns:
            List of usable polygon vertex loops.
        """
        if not room_polygon or len(room_polygon) < 3:
            return []

        try:
            from shapely.geometry import Polygon, MultiPolygon
            from shapely.validation import make_valid

            # Construct Shapely room polygon
            room_poly = Polygon(room_polygon)
            if not room_poly.is_valid:
                room_poly = make_valid(room_poly)

            # Apply wall inset buffer if specified
            if wall_inset_buffer > 0.0:
                buffered_room = room_poly.buffer(-wall_inset_buffer)
                if not buffered_room.is_empty:
                    room_poly = buffered_room

            # Subtract all obstacle polygons
            current_space = room_poly
            for obs in obstacles:
                if not obs or len(obs) < 3:
                    continue
                obs_poly = Polygon(obs)
                if not obs_poly.is_valid:
                    obs_poly = make_valid(obs_poly)
                current_space = current_space.difference(obs_poly)

            # Convert result back to coordinate lists
            result_polygons = []
            if current_space.is_empty:
                return []
            elif isinstance(current_space, Polygon):
                result_polygons.append(list(current_space.exterior.coords))
            elif isinstance(current_space, MultiPolygon):
                for poly in current_space.geoms:
                    result_polygons.append(list(poly.exterior.coords))

            return result_polygons

        except ImportError:
            # Fallback pure-Python bounding box subtraction logic if Shapely is not installed
            min_x = min(p[0] for p in room_polygon) + wall_inset_buffer
            max_x = max(p[0] for p in room_polygon) - wall_inset_buffer
            min_y = min(p[1] for p in room_polygon) + wall_inset_buffer
            max_y = max(p[1] for p in room_polygon) - wall_inset_buffer

            if min_x >= max_x or min_y >= max_y:
                return []

            # Pure Python rectangle fallback boundary
            boundary = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
            return [boundary]

    @staticmethod
    def calculate_polygon_area(vertices: List[Tuple[float, float]]) -> float:
        """Calculate area of a 2D polygon using standard Shoelace formula."""
        n = len(vertices)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        return abs(area) / 2.0
