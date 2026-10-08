"""
Floor Plan Geometry Reconciliation and Verification Engine (Task 2.3).
Performs authoritative Shapely-derived boundary validation, topological area computation,
polygon validity checks, anomaly warning detection, and Layouts Team human verification workflows
for ingested IFC and DXF floor plan models.
"""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

try:
    from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
    from shapely.ops import unary_union
    from shapely import make_valid
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

from app.bim.ifc_ingest import IFCParsedFloorPlan, GeometryStatus, GeometryType, Geometry2D, shapely_to_geometry_model
from app.bim.dxf_ingest import DXFParsedFloorPlan, DXFEntity


class VerificationStatus(str, Enum):
    """Status of human verification for an ingested floor plan baseline."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class GeometryAnomalyWarning(BaseModel):
    """Details of a geometry anomaly detected during floor plan ingestion reconciliation."""
    model_config = ConfigDict(extra="forbid")

    warning_id: str
    warning_type: str = Field(..., description="e.g. 'UNCLOSED_POLYGON', 'MISSING_DOORS', 'MISSING_WALLS', 'INVALID_GEOMETRY', 'GEOMETRY_REPAIRED'")
    severity: str = Field(default="WARNING", description="Severity level: 'WARNING' or 'CRITICAL'")
    element_id: Optional[str] = Field(None, description="GlobalId or element name affected")
    message: str = Field(..., description="Explanation for Layouts Team review")


class GeometryVerificationReport(BaseModel):
    """Complete verification report generated for Layouts Team quality review."""
    model_config = ConfigDict(extra="forbid")

    floor_plan_name: str
    source_type: str = Field(default="IFC", description="Source format ('IFC' or 'DXF')")
    is_geometry_valid: bool = Field(..., description="True if no critical geometry flaws prevent optimization")
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING, description="Human verification status")
    total_rooms_count: int = Field(..., description="Count of valid room/space boundaries")
    total_net_area_sqm: float = Field(..., description="Total floor net area in square meters calculated from geometry")
    boundary_polygon: List[List[float]] = Field(default_factory=list, description="Simple exterior ring vertices [[x,y],...] for backward compatibility")
    boundary_geometry: Optional[Geometry2D] = Field(default=None, description="Authoritative GeoJSON Geometry2D (Polygon or MultiPolygon with holes)")
    elements_summary: Dict[str, Any] = Field(default_factory=dict, description="Counts of extracted walls, doors, windows, columns, spaces, furniture_items")
    all_elements_geometry: List[Dict[str, Any]] = Field(default_factory=list, description="List of vector elements for read-only UI rendering")
    available_storeys: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="IFC building-storey summary used by the 2D editor to select one floor at a time",
    )
    recommended_storey: Optional[str] = Field(
        default=None,
        description="Deterministically selected default IFC storey for the 2D editor",
    )
    warnings: List[GeometryAnomalyWarning] = Field(default_factory=list)
    reviewer_user_id: Optional[str] = Field(None, description="User ID of Layouts Team reviewer who verified/rejected")
    verified_at: Optional[str] = Field(None, description="ISO timestamp of human verification action")
    rejection_reason: Optional[str] = Field(None, description="Mandatory reason required when rejecting a floor plan")


class GeometryReconciler:
    """Engine verifying and reconciling ingested floor plan geometries deterministically."""

    def reconcile_ifc(self, parsed_ifc: IFCParsedFloorPlan) -> GeometryVerificationReport:
        """
        Reconcile and generate verification report for parsed IFC floor plan.
        Operates on actual parsed IfcOpenShell geometry and Shapely topology.
        Zero hard-coded production geometry or fake fallbacks.
        """
        warnings: List[GeometryAnomalyWarning] = []
        valid_space_polys: List[Polygon] = []
        total_area = 0.0
        elements_geom: List[Dict[str, Any]] = []

        all_elements = (
            parsed_ifc.walls +
            parsed_ifc.doors +
            parsed_ifc.windows +
            parsed_ifc.columns +
            parsed_ifc.spaces +
            getattr(parsed_ifc, "furniture", [])
        )

        for elem in all_elements:
            if elem.geometry_status == GeometryStatus.VALID and elem.geometry_coordinates:
                cat_name = elem.category if hasattr(elem, "category") and elem.category else "FURNITURE_ITEM"
                sub_type = elem.subtype if hasattr(elem, "subtype") and elem.subtype else "OTHER"
                elem_name = elem.name if (elem.name and elem.name not in ("Polygon", "MultiPolygon")) else elem.element_type

                elements_geom.append({
                    "id": elem.internal_id,
                    "global_id": elem.ifc_global_id,
                    "category": cat_name,
                    "subtype": sub_type,
                    "element_type": elem.element_type,
                    "name": elem_name,
                    "geometry_type": elem.geometry_type.value if hasattr(elem.geometry_type, "value") else str(elem.geometry_type),
                    "type": elem.geometry_type.value if hasattr(elem.geometry_type, "value") else str(elem.geometry_type),
                    "coordinates": elem.geometry_coordinates,
                    "boundary": elem.boundary_vertices,
                    "storey_id": elem.properties.get("storey_id"),
                    "storey_name": elem.properties.get("storey_name"),
                    "storey_elevation_m": elem.properties.get("storey_elevation_m"),
                    "properties": elem.properties,
                })

        # Reconcile Spaces
        for idx, space in enumerate(parsed_ifc.spaces):
            if space.geometry_status == GeometryStatus.VALID and space.geometry_coordinates:
                try:
                    poly = self._coords_to_shapely(space.geometry_type, space.geometry_coordinates)
                    if poly is not None and not poly.is_empty:
                        if not poly.is_valid:
                            repaired = make_valid(poly) if hasattr(make_valid, "__call__") else poly.buffer(0)
                            if repaired.is_valid and not repaired.is_empty:
                                poly = repaired
                                warnings.append(GeometryAnomalyWarning(
                                    warning_id=f"warn_repair_{idx+1}",
                                    warning_type="GEOMETRY_REPAIRED",
                                    severity="WARNING",
                                    element_id=space.ifc_global_id,
                                    message=f"Space geometry for {space.name} ({space.ifc_global_id}) had self-intersections and was repaired via make_valid."
                                ))
                        if poly.is_valid and poly.area > 1e-4:
                            valid_space_polys.append(poly)
                            total_area += float(poly.area)
                except Exception as err:
                    warnings.append(GeometryAnomalyWarning(
                        warning_id=f"warn_invalid_space_{idx+1}",
                        warning_type="INVALID_GEOMETRY",
                        severity="WARNING",
                        element_id=space.ifc_global_id,
                        message=f"Failed to reconcile space geometry for {space.ifc_global_id}: {str(err)}"
                    ))

        # Build deterministic building-storey summaries from the parsed IFC spatial containers.
        # The report still contains every source element, but the frontend can now select
        # exactly one building storey for a coherent 2D floor-plan view.
        storey_summary_by_name: Dict[str, Dict[str, Any]] = {}
        for elem in all_elements:
            props = elem.properties or {}
            storey_name = props.get("storey_name")
            if not storey_name:
                continue

            summary = storey_summary_by_name.setdefault(
                str(storey_name),
                {
                    "name": str(storey_name),
                    "storey_id": props.get("storey_id"),
                    "elevation_m": props.get("storey_elevation_m"),
                    "element_count": 0,
                    "wall_count": 0,
                    "door_count": 0,
                    "window_count": 0,
                    "column_count": 0,
                    "space_count": 0,
                    "furniture_count": 0,
                },
            )
            summary["element_count"] += 1

            category = str(getattr(elem, "category", "") or "").upper()
            if "WALL" in category:
                summary["wall_count"] += 1
            elif "DOOR" in category:
                summary["door_count"] += 1
            elif "WINDOW" in category:
                summary["window_count"] += 1
            elif "COLUMN" in category:
                summary["column_count"] += 1
            elif "SPACE" in category or "ROOM" in category:
                summary["space_count"] += 1
            elif "FURNITURE" in category:
                summary["furniture_count"] += 1

        available_storeys = sorted(
            storey_summary_by_name.values(),
            key=lambda item: (
                item["elevation_m"] is None,
                item["elevation_m"] if item["elevation_m"] is not None else 0.0,
                item["name"],
            ),
        )

        recommended_storey = None
        if available_storeys:
            recommended_storey = max(
                available_storeys,
                key=lambda item: (
                    item["space_count"],
                    item["wall_count"],
                    item["element_count"],
                    -(
                        item["elevation_m"]
                        if item["elevation_m"] is not None
                        else 0.0
                    ),
                    item["name"],
                ),
            )["name"]

        # Check missing elements
        if len(parsed_ifc.spaces) == 0 or len(valid_space_polys) == 0:
            warnings.append(GeometryAnomalyWarning(
                warning_id="warn_no_spaces",
                warning_type="MISSING_ROOM_GEOMETRY",
                severity="WARNING" if len(parsed_ifc.walls) > 0 else "CRITICAL",
                message="No valid 2D room/space footprint geometry detected in IFC model."
            ))

        if len(parsed_ifc.doors) == 0:
            warnings.append(GeometryAnomalyWarning(
                warning_id="warn_no_doors",
                warning_type="MISSING_DOORS",
                severity="WARNING",
                message="No door entities detected in floor plan. Please verify entrance access."
            ))

        if len(parsed_ifc.walls) == 0:
            warnings.append(GeometryAnomalyWarning(
                warning_id="warn_no_walls",
                warning_type="MISSING_WALLS",
                severity="CRITICAL",
                message="No structural wall entities detected in IFC model."
            ))

        # Outer boundary union calculation
        boundary_geom_model = None
        boundary_compat: List[List[float]] = []

        if valid_space_polys:
            try:
                unioned = unary_union(valid_space_polys)
                if not unioned.is_valid:
                    unioned = unioned.buffer(0)
                if not unioned.is_empty:
                    g_type, g_coords, b_compat = shapely_to_geometry_model(unioned)
                    boundary_geom_model = Geometry2D(type=g_type, coordinates=g_coords)
                    boundary_compat = b_compat
            except Exception as err:
                warnings.append(GeometryAnomalyWarning(
                    warning_id="warn_boundary_union_failed",
                    warning_type="INVALID_GEOMETRY",
                    severity="WARNING",
                    message=f"Failed to compute outer boundary union from space polygons: {str(err)}"
                ))
        else:
            # Fallback: compute boundary union from wall footprint polygons
            valid_wall_polys = []
            for w in parsed_ifc.walls:
                if w.geometry_status == GeometryStatus.VALID and w.geometry_coordinates:
                    try:
                        poly = self._coords_to_shapely(w.geometry_type, w.geometry_coordinates)
                        if poly is not None and not poly.is_empty and poly.is_valid:
                            valid_wall_polys.append(poly)
                    except Exception:
                        pass
            if valid_wall_polys:
                try:
                    unioned_walls = unary_union(valid_wall_polys)
                    if not unioned_walls.is_valid:
                        unioned_walls = unioned_walls.buffer(0)
                    if not unioned_walls.is_empty:
                        hull = unioned_walls.convex_hull
                        if hull.is_valid and not hull.is_empty:
                            g_type, g_coords, b_compat = shapely_to_geometry_model(hull)
                            boundary_geom_model = Geometry2D(type=g_type, coordinates=g_coords)
                            boundary_compat = b_compat
                except Exception:
                    pass

        furniture_items = getattr(parsed_ifc, "furniture", [])

        furniture_breakdown: Dict[str, int] = {}
        for item in furniture_items:
            st = item.subtype.lower() if hasattr(item, "subtype") and item.subtype else "other"
            furniture_breakdown[st] = furniture_breakdown.get(st, 0) + 1

        elem_summary: Dict[str, Any] = {
            "walls": len(parsed_ifc.walls),
            "doors": len(parsed_ifc.doors),
            "windows": len(parsed_ifc.windows),
            "columns": len(parsed_ifc.columns),
            "spaces": len(parsed_ifc.spaces),
            "furniture_items": len(furniture_items),
        }
        if furniture_breakdown:
            elem_summary["furniture_breakdown"] = furniture_breakdown

        has_critical_error = any(w.severity == "CRITICAL" for w in warnings)

        return GeometryVerificationReport(
            floor_plan_name=parsed_ifc.file_name,
            source_type="IFC",
            is_geometry_valid=not has_critical_error,
            verification_status=VerificationStatus.PENDING,
            total_rooms_count=len(valid_space_polys),
            total_net_area_sqm=round(total_area, 2),
            boundary_polygon=boundary_compat,
            boundary_geometry=boundary_geom_model,
            elements_summary=elem_summary,
            all_elements_geometry=elements_geom,
            available_storeys=available_storeys,
            recommended_storey=recommended_storey,
            warnings=warnings,
        )

    def reconcile_dxf(self, parsed_dxf: DXFParsedFloorPlan) -> GeometryVerificationReport:
        """
        Reconcile and generate verification report for parsed 2D DXF floor plan.
        Operates on actual parsed ezdxf geometry and Shapely topology.
        Zero hard-coded production geometry or fake fallbacks.
        """
        warnings: List[GeometryAnomalyWarning] = []
        valid_space_polys: List[Polygon] = []
        valid_wall_polys: List[Polygon] = []
        total_area = 0.0
        elements_geom: List[Dict[str, Any]] = []

        for idx, elem in enumerate(parsed_dxf.extracted_entities):
            elements_geom.append({
                "id": f"dxf_{elem.entity_type.lower()}_{idx+1}",
                "global_id": f"dxf_{elem.layer_name}_{idx+1}",
                "category": elem.category,
                "type": elem.entity_type,
                "coordinates": elem.coordinates,
                "is_closed": elem.is_closed,
            })

            # Check unclosed wall polylines
            if elem.category == "WALL" and not elem.is_closed and elem.entity_type in ("LWPOLYLINE", "POLYLINE"):
                warnings.append(GeometryAnomalyWarning(
                    warning_id=f"warn_unclosed_wall_{idx+1}",
                    warning_type="UNCLOSED_POLYGON",
                    severity="WARNING",
                    element_id=f"layer:{elem.layer_name}",
                    message=f"Wall polyline on layer '{elem.layer_name}' is unclosed."
                ))

            # Collect closed space polygons
            if elem.category == "SPACE" and elem.is_closed and len(elem.coordinates) >= 3:
                try:
                    poly = Polygon(elem.coordinates)
                    if not poly.is_valid:
                        poly = poly.buffer(0)
                    if poly.is_valid and poly.area > 1e-4:
                        valid_space_polys.append(poly)
                        total_area += float(poly.area)
                except Exception as err:
                    warnings.append(GeometryAnomalyWarning(
                        warning_id=f"warn_invalid_space_{idx+1}",
                        warning_type="INVALID_GEOMETRY",
                        severity="WARNING",
                        element_id=f"layer:{elem.layer_name}",
                        message=f"Invalid space polygon on layer '{elem.layer_name}': {str(err)}"
                    ))

            # Collect closed wall polygons for fallback boundary calculation
            if elem.category == "WALL" and elem.is_closed and len(elem.coordinates) >= 3:
                try:
                    poly = Polygon(elem.coordinates)
                    if not poly.is_valid:
                        poly = poly.buffer(0)
                    if poly.is_valid and poly.area > 1e-4:
                        valid_wall_polys.append(poly)
                except Exception:
                    pass

        # Check missing categories
        wall_count = parsed_dxf.entities_by_category.get("WALL", 0)
        door_count = parsed_dxf.entities_by_category.get("DOOR", 0)

        if wall_count == 0:
            warnings.append(GeometryAnomalyWarning(
                warning_id="warn_dxf_no_walls",
                warning_type="MISSING_WALLS",
                severity="CRITICAL",
                message="No structural wall entities detected in DXF drawing."
            ))

        if door_count == 0:
            warnings.append(GeometryAnomalyWarning(
                warning_id="warn_dxf_no_doors",
                warning_type="MISSING_DOORS",
                severity="WARNING",
                message="No door entities detected in DXF drawing."
            ))

        if len(valid_space_polys) == 0:
            if len(valid_wall_polys) > 0:
                warnings.append(GeometryAnomalyWarning(
                    warning_id="warn_dxf_no_space_polys",
                    warning_type="MISSING_ROOM_GEOMETRY",
                    severity="WARNING",
                    message="No explicit DXF space/room layer polylines found; boundary derived from wall geometry."
                ))
            else:
                warnings.append(GeometryAnomalyWarning(
                    warning_id="warn_dxf_no_space_polys",
                    warning_type="MISSING_ROOM_GEOMETRY",
                    severity="WARNING",
                    message="No valid 2D room or space footprint boundaries found in DXF CAD drawing."
                ))

        # Compute outer boundary from space polygons or fallback wall polygons
        boundary_target_polys = valid_space_polys or valid_wall_polys
        boundary_geom_model = None
        boundary_compat: List[List[float]] = []

        if boundary_target_polys:
            try:
                unioned = unary_union(boundary_target_polys)
                if not unioned.is_valid:
                    unioned = unioned.buffer(0)
                if not unioned.is_empty:
                    g_type, g_coords, b_compat = shapely_to_geometry_model(unioned)
                    boundary_geom_model = Geometry2D(type=g_type, coordinates=g_coords)
                    boundary_compat = b_compat
            except Exception as err:
                warnings.append(GeometryAnomalyWarning(
                    warning_id="warn_dxf_boundary_failed",
                    warning_type="INVALID_GEOMETRY",
                    severity="WARNING",
                    message=f"Failed to compute outer boundary union for DXF drawing: {str(err)}"
                ))

        has_critical_error = any(w.severity == "CRITICAL" for w in warnings)

        return GeometryVerificationReport(
            floor_plan_name=parsed_dxf.file_name,
            source_type="DXF",
            is_geometry_valid=not has_critical_error,
            verification_status=VerificationStatus.PENDING,
            total_rooms_count=len(valid_space_polys),
            total_net_area_sqm=round(total_area, 2),
            boundary_polygon=boundary_compat,
            boundary_geometry=boundary_geom_model,
            elements_summary=dict(parsed_dxf.entities_by_category),
            all_elements_geometry=elements_geom,
            warnings=warnings,
        )

    def _coords_to_shapely(self, geom_type: Optional[Any], coords: Any) -> Optional[Union[Polygon, MultiPolygon]]:
        """Helper converting GeoJSON Geometry2D coordinates to Shapely Polygon or MultiPolygon."""
        if not geom_type or not coords:
            return None

        type_str = geom_type.value if hasattr(geom_type, "value") else str(geom_type)

        if type_str == "Polygon":
            exterior = coords[0]
            interiors = coords[1:] if len(coords) > 1 else None
            return Polygon(shell=exterior, holes=interiors)

        elif type_str == "MultiPolygon":
            polys = []
            for poly_rings in coords:
                ext = poly_rings[0]
                holes = poly_rings[1:] if len(poly_rings) > 1 else None
                polys.append(Polygon(shell=ext, holes=holes))
            return MultiPolygon(polys)

        return None
