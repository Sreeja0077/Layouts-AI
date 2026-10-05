"""
Authoritative Free-Space Polygon & Obstacle Subtraction Engine (Task 4.1).
Calculates deterministic 2D usable placement areas inside rooms by applying perimeter
wall insets, subtracting structural obstacles (columns, internal walls, door swing arcs)
with clearance buffers, and preserving complete geometry topology (interior holes and MultiPolygons).
Powered authoritatively by Shapely / GEOS.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon
    from shapely.ops import unary_union
    from shapely.validation import make_valid
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


def _check_shapely_available() -> None:
    """Enforce authoritative Shapely/GEOS availability invariant."""
    if not HAS_SHAPELY:
        raise ImportError(
            "Shapely/GEOS is required for authoritative free-space geometry calculation. "
            "Silent bounding-box approximations or fake geometry fallbacks are strictly prohibited."
        )


class FreeSpaceEngine:
    """Deterministic 2D polygon free space computation engine powered by Shapely/GEOS."""

    @staticmethod
    def compute_usable_geometry(
        room_polygon: Union[List[Tuple[float, float]], Polygon, MultiPolygon],
        obstacles: Optional[List[Union[List[Tuple[float, float]], Polygon, MultiPolygon]]] = None,
        wall_inset_buffer: float = 0.0,
        obstacle_clearance_buffer: float = 0.0,
    ) -> Union[Polygon, MultiPolygon]:
        """
        Compute authoritative Shapely free-space geometry inside a room.

        Args:
            room_polygon: Outer room boundary vertices [(x, y)...] or Shapely Polygon/MultiPolygon.
            obstacles: List of obstacle coordinate lists [(x, y)...] or Shapely Polygons (columns, door swings, walls).
            wall_inset_buffer: Safety perimeter wall inset distance in meters.
            obstacle_clearance_buffer: Clearance buffer distance in meters expanded around obstacles before subtraction.

        Returns:
            Shapely Polygon or MultiPolygon representing net usable free space (or empty Polygon()).
        """
        _check_shapely_available()

        # 1. Parse and validate room geometry
        if isinstance(room_polygon, (Polygon, MultiPolygon)):
            room_geom = room_polygon
        elif isinstance(room_polygon, list) and len(room_polygon) >= 3:
            room_geom = Polygon(room_polygon)
        else:
            return Polygon()

        if not room_geom.is_valid:
            room_geom = make_valid(room_geom)

        if room_geom.is_empty:
            return Polygon()

        # 2. Apply wall perimeter inset buffer
        if wall_inset_buffer > 0.0:
            buffered_room = room_geom.buffer(-wall_inset_buffer)
            if not buffered_room.is_valid:
                buffered_room = make_valid(buffered_room)
            if buffered_room.is_empty:
                return Polygon()
            room_geom = buffered_room

        # 3. Parse, validate, and buffer obstacles
        if not obstacles:
            return room_geom

        parsed_obstacles = []
        for obs in obstacles:
            if not obs:
                continue
            if isinstance(obs, (Polygon, MultiPolygon)):
                obs_geom = obs
            elif isinstance(obs, list) and len(obs) >= 3:
                obs_geom = Polygon(obs)
            else:
                continue

            if not obs_geom.is_valid:
                obs_geom = make_valid(obs_geom)

            if obs_geom.is_empty:
                continue

            # Apply obstacle clearance buffer if requested
            if obstacle_clearance_buffer > 0.0:
                obs_geom = obs_geom.buffer(obstacle_clearance_buffer)
                if not obs_geom.is_valid:
                    obs_geom = make_valid(obs_geom)

            parsed_obstacles.append(obs_geom)

        if not parsed_obstacles:
            return room_geom

        # 4. Subtract unioned obstacles from usable room area
        obstacles_union = unary_union(parsed_obstacles)
        usable_geom = room_geom.difference(obstacles_union)

        if not usable_geom.is_valid:
            usable_geom = make_valid(usable_geom)

        if usable_geom.is_empty:
            return Polygon()

        # Filter out 0D/1D artifacts (Points/LineStrings) if difference creates GeometryCollection
        if isinstance(usable_geom, GeometryCollection):
            polys = [g for g in usable_geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
            if not polys:
                return Polygon()
            usable_geom = unary_union(polys)

        return usable_geom

    @staticmethod
    def compute_usable_freespace(
        room_polygon: Union[List[Tuple[float, float]], Polygon, MultiPolygon],
        obstacles: Optional[List[Union[List[Tuple[float, float]], Polygon, MultiPolygon]]] = None,
        wall_inset_buffer: float = 0.0,
        obstacle_clearance_buffer: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Compute GeoJSON-compatible free-space dictionary preserving complete topology (holes and MultiPolygons).

        Returns:
            Dict containing:
                "type": "Polygon" or "MultiPolygon"
                "coordinates": GeoJSON coordinates preserving exterior rings and interior holes
                "area_sqm": Authoritative net placement area in square meters
                "is_empty": bool
                "boundary_vertices": List[List[float]] outer shell compat ring (or [] if multi/holes)
        """
        usable_geom = FreeSpaceEngine.compute_usable_geometry(
            room_polygon=room_polygon,
            obstacles=obstacles,
            wall_inset_buffer=wall_inset_buffer,
            obstacle_clearance_buffer=obstacle_clearance_buffer,
        )

        return FreeSpaceEngine.serialize_geometry(usable_geom)

    @staticmethod
    def serialize_geometry(geom: Any, decimals: int = 4) -> Dict[str, Any]:
        """Convert a Shapely Polygon or MultiPolygon into a GeoJSON-compatible dictionary preserving all rings."""
        _check_shapely_available()

        if geom is None or geom.is_empty:
            return {
                "type": "Polygon",
                "coordinates": [],
                "area_sqm": 0.0,
                "is_empty": True,
                "boundary_vertices": [],
            }

        if geom.geom_type == "Polygon":
            ext_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in geom.exterior.coords]
            rings = [ext_coords]
            has_holes = len(geom.interiors) > 0

            for interior in geom.interiors:
                hole_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in interior.coords]
                rings.append(hole_coords)

            ext_compat = (
                ext_coords[:-1]
                if (not has_holes and len(ext_coords) > 1 and ext_coords[0] == ext_coords[-1])
                else ext_coords
            )

            return {
                "type": "Polygon",
                "coordinates": rings,
                "area_sqm": round(geom.area, decimals),
                "is_empty": False,
                "boundary_vertices": ext_compat,
            }

        elif geom.geom_type == "MultiPolygon":
            multi_coords = []
            for poly in geom.geoms:
                poly_rings = []
                ext_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in poly.exterior.coords]
                poly_rings.append(ext_coords)
                for interior in poly.interiors:
                    hole_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in interior.coords]
                    poly_rings.append(hole_coords)
                multi_coords.append(poly_rings)

            return {
                "type": "MultiPolygon",
                "coordinates": multi_coords,
                "area_sqm": round(geom.area, decimals),
                "is_empty": False,
                "boundary_vertices": [],
            }

        return {
            "type": "Polygon",
            "coordinates": [],
            "area_sqm": 0.0,
            "is_empty": True,
            "boundary_vertices": [],
        }

    @staticmethod
    def calculate_freespace_area(
        freespace_input: Union[Any, Dict[str, Any], List[Tuple[float, float]], List[List[Tuple[float, float]]]]
    ) -> float:
        """
        Calculate authoritative net area in square meters.
        Automatically subtracts interior hole areas and handles MultiPolygons.
        """
        if not freespace_input:
            return 0.0

        if HAS_SHAPELY and isinstance(freespace_input, (Polygon, MultiPolygon)):
            return float(freespace_input.area)

        if isinstance(freespace_input, dict):
            return float(freespace_input.get("area_sqm", 0.0))

        # If passed a single list of 2D points [(x, y)...]
        if (
            isinstance(freespace_input, list)
            and freespace_input
            and isinstance(freespace_input[0], (tuple, list))
            and isinstance(freespace_input[0][0], (int, float))
        ):
            return FreeSpaceEngine.calculate_polygon_area(freespace_input)

        # If passed a list of rings [[outer_ring], [hole1], [hole2]...]
        if isinstance(freespace_input, list) and freespace_input and isinstance(freespace_input[0], list):
            total = FreeSpaceEngine.calculate_polygon_area(freespace_input[0])
            for hole in freespace_input[1:]:
                total -= FreeSpaceEngine.calculate_polygon_area(hole)
            return max(0.0, total)

        return 0.0

    @staticmethod
    def calculate_polygon_area(vertices: List[Tuple[float, float]]) -> float:
        """Calculate area of a single 2D polygon loop using standard Shoelace formula."""
        n = len(vertices)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        return abs(area) / 2.0
