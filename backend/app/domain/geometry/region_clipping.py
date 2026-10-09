"""
Authoritative Server-Side Region Clipping and Geometry Validation Service (Task 6.3).
Uses Shapely make_valid to clip user-drawn freehand regions against authoritative
persisted IFC architectural boundaries in pure world coordinates (meters).
"""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, shape
from shapely.ops import unary_union
from shapely.validation import make_valid


class RegionValidationStatus(str, Enum):
    VALID = "VALID"
    CLIPPED = "CLIPPED"
    NO_OVERLAP = "NO_OVERLAP"
    INVALID_INPUT = "INVALID_INPUT"
    FAILED = "FAILED"


class Point2DModel(BaseModel):
    """2D Point in world metric coordinates (meters)."""
    model_config = ConfigDict(extra="forbid")
    x: float = Field(..., description="X coordinate in world meters")
    y: float = Field(..., description="Y coordinate in world meters")

    @field_validator("x", "y")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Coordinate values must be finite numbers")
        return round(float(v), 4)


class ValidateRegionRequest(BaseModel):
    """Request payload for server-side region validation and clipping."""
    model_config = ConfigDict(extra="forbid")
    floor_plan_id: str = Field(..., min_length=1, description="Floor plan identifier")
    storey_name: Optional[str] = Field(None, description="Optional target storey name")
    world_points: List[Point2DModel] = Field(..., min_length=3, description="User polygon vertices in world meters")


class ValidatedRegionResponse(BaseModel):
    """Authoritative response containing server-clipped polygon and geometry metrics."""
    model_config = ConfigDict(extra="forbid")
    status: RegionValidationStatus = Field(..., description="Validation and clipping status")
    is_valid: bool = Field(..., description="True if valid non-empty polygonal region was produced")
    is_clipped: bool = Field(..., description="True if user polygon was modified/trimmed by boundary")
    message: str = Field(..., description="Human-readable status summary")
    floor_plan_id: str = Field(..., description="Floor plan identifier")
    storey_name: Optional[str] = Field(None, description="Target storey name used for clipping")
    submitted_points: List[Point2DModel] = Field(..., description="Original submitted vertices")
    clipped_points: List[Point2DModel] = Field(default_factory=list, description="Authoritative exterior vertices")
    clipped_polygons: Optional[List[List[Point2DModel]]] = Field(None, description="MultiPolygon components if applicable")
    area_sqm: float = Field(default=0.0, ge=0.0, description="Enclosed surface area in square meters")
    perimeter_m: float = Field(default=0.0, ge=0.0, description="Boundary perimeter length in meters")
    centroid: Optional[Point2DModel] = Field(None, description="Area-weighted centroid in world meters")


def extract_polygon_components(geom: Any) -> List[Polygon]:
    """Extract pure 2D Polygon instances from any Shapely geometry or GeometryCollection."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > 1e-6 else []
    if isinstance(geom, MultiPolygon):
        return [p for p in geom.geoms if p.area > 1e-6]
    if isinstance(geom, GeometryCollection):
        polys = []
        for g in geom.geoms:
            polys.extend(extract_polygon_components(g))
        return polys
    return []


def construct_shapely_polygon(points: List[Point2DModel]) -> Polygon | MultiPolygon:
    """
    Construct a valid Shapely Polygon or MultiPolygon from input vertices.
    Uses make_valid to repair self-intersections or bowtie topology without convex-hull distortion.
    """
    if len(points) < 3:
        raise ValueError("Polygon requires at least 3 vertices")

    coords = [(p.x, p.y) for p in points]
    # Ensure closed ring for Shapely
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    poly = Polygon(coords)
    if not poly.is_valid:
        poly = make_valid(poly)

    polys = extract_polygon_components(poly)
    if not polys:
        raise ValueError("Provided points do not form a valid polygonal area")

    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)


def extract_authoritative_boundary_from_report(
    report_dict: Dict[str, Any],
    target_storey: Optional[str] = None,
) -> Tuple[Optional[Polygon | MultiPolygon], Optional[str]]:
    """
    Extract the authoritative room/space boundary for the requested storey from the persisted verification report.
    Reuses the repository's existing IFC spatial geometry convention without fabricating synthetic rooms.
    """
    from app.api.v1.layout import _element_geometry, _element_storey_name, _resolve_target_storey

    all_elements = report_dict.get("all_elements_geometry", [])
    resolved_storey = _resolve_target_storey(report_dict, target_storey)

    if resolved_storey:
        storey_elements = [
            elem
            for elem in all_elements
            if _element_storey_name(elem) == resolved_storey
        ]
    else:
        storey_elements = list(all_elements)

    # 1. Primary: Use real IFC SPACE footprints
    space_geoms = [
        geom
        for elem in storey_elements
        if "SPACE" in str(elem.get("category", "")).upper()
        and (geom := _element_geometry(elem)) is not None
    ]

    # Fallback to all spaces in report if storey filter yielded none (e.g. spaces without explicit storey tags)
    if not space_geoms:
        space_geoms = [
            geom
            for elem in all_elements
            if "SPACE" in str(elem.get("category", "")).upper()
            and (geom := _element_geometry(elem)) is not None
        ]

    boundary_geom: Optional[Polygon | MultiPolygon] = None

    if space_geoms:
        boundary_geom = unary_union(space_geoms)
        if not boundary_geom.is_valid:
            boundary_geom = make_valid(boundary_geom)

    if boundary_geom is None or boundary_geom.is_empty:
        # 2. Fallback: Structural elements (WALL, COLUMN) if no explicit spaces
        candidate_geoms = [
            geom
            for elem in storey_elements
            if elem.get("category") in ("WALL", "COLUMN")
            and (geom := _element_geometry(elem)) is not None
        ]
        if not candidate_geoms:
            candidate_geoms = [
                geom
                for elem in all_elements
                if elem.get("category") in ("WALL", "COLUMN")
                and (geom := _element_geometry(elem)) is not None
            ]
        if candidate_geoms:
            boundary_geom = unary_union(candidate_geoms).convex_hull
            if not boundary_geom.is_valid:
                boundary_geom = make_valid(boundary_geom)

    if boundary_geom is not None and not boundary_geom.is_empty:
        # Translate to (0, 0) origin matching normalizeFloorPlanRenderModel and _extract_room_entity_from_report
        min_x, min_y, _, _ = boundary_geom.bounds
        if abs(min_x) > 1e-4 or abs(min_y) > 1e-4:
            from shapely.affinity import translate
            boundary_geom = translate(boundary_geom, xoff=-min_x, yoff=-min_y)
        return boundary_geom, resolved_storey

    return None, resolved_storey



def clip_region_to_boundary(
    user_points: List[Point2DModel],
    boundary_geom: Polygon | MultiPolygon,
    floor_plan_id: str,
    storey_name: Optional[str] = None,
) -> ValidatedRegionResponse:
    """
    Clips a user world-space polygon against the authoritative architectural boundary using Shapely make_valid.
    Computes precise area, perimeter, and centroid on the resulting valid geometry.
    """
    submitted_points = [Point2DModel(x=p.x, y=p.y) for p in user_points]

    # 1. Build and validate user polygon
    try:
        user_poly = construct_shapely_polygon(user_points)
    except ValueError as val_err:
        return ValidatedRegionResponse(
            status=RegionValidationStatus.INVALID_INPUT,
            is_valid=False,
            is_clipped=False,
            message=str(val_err),
            floor_plan_id=floor_plan_id,
            storey_name=storey_name,
            submitted_points=submitted_points,
            clipped_points=[],
            area_sqm=0.0,
            perimeter_m=0.0,
            centroid=None,
        )

    # 2. Ensure architectural boundary is valid
    if not boundary_geom.is_valid:
        boundary_geom = make_valid(boundary_geom)

    # 3. Perform geometric intersection (clipping)
    intersection_geom = user_poly.intersection(boundary_geom)
    if not intersection_geom.is_valid:
        intersection_geom = make_valid(intersection_geom)

    polys = extract_polygon_components(intersection_geom)
    if not polys or intersection_geom.is_empty or intersection_geom.area <= 1e-6:
        return ValidatedRegionResponse(
            status=RegionValidationStatus.NO_OVERLAP,
            is_valid=False,
            is_clipped=True,
            message="Selected region is completely outside the authoritative architectural boundary",
            floor_plan_id=floor_plan_id,
            storey_name=storey_name,
            submitted_points=submitted_points,
            clipped_points=[],
            area_sqm=0.0,
            perimeter_m=0.0,
            centroid=None,
        )

    # Select primary or largest polygon for standard representation, and include all if MultiPolygon
    primary_poly = max(polys, key=lambda p: p.area)
    clipped_points = [
        Point2DModel(x=float(x), y=float(y))
        for x, y in primary_poly.exterior.coords
    ]
    # Remove duplicate closing point for cleaner consumer usage if present
    if len(clipped_points) > 1 and clipped_points[0] == clipped_points[-1]:
        clipped_points.pop()

    all_polys_coords: Optional[List[List[Point2DModel]]] = None
    if len(polys) > 1:
        all_polys_coords = []
        for p in polys:
            p_pts = [Point2DModel(x=float(x), y=float(y)) for x, y in p.exterior.coords]
            if len(p_pts) > 1 and p_pts[0] == p_pts[-1]:
                p_pts.pop()
            all_polys_coords.append(p_pts)

    total_area = float(intersection_geom.area)
    total_perimeter = float(sum(p.length for p in polys))
    c = intersection_geom.centroid
    centroid = Point2DModel(x=float(c.x), y=float(c.y)) if (c and not c.is_empty) else None

    # Check if user polygon was actually clipped/trimmed
    user_area = float(user_poly.area)
    is_clipped = abs(user_area - total_area) > 1e-3

    status_code = RegionValidationStatus.CLIPPED if is_clipped else RegionValidationStatus.VALID
    message = (
        f"Region successfully clipped to architectural boundary ({round(total_area, 2)} m²)"
        if is_clipped
        else f"Region fully enclosed within architectural boundary ({round(total_area, 2)} m²)"
    )

    return ValidatedRegionResponse(
        status=status_code,
        is_valid=True,
        is_clipped=is_clipped,
        message=message,
        floor_plan_id=floor_plan_id,
        storey_name=storey_name,
        submitted_points=submitted_points,
        clipped_points=clipped_points,
        clipped_polygons=all_polys_coords,
        area_sqm=round(total_area, 4),
        perimeter_m=round(total_perimeter, 4),
        centroid=centroid,
    )
