"""
Revit IFC (Industry Foundation Classes) Floor Plan Ingestion Engine.
Extracts structural elements (IfcWall, IfcDoor, IfcWindow, IfcColumn, IfcSpace)
and calculates 2D footprint polygon geometry using IfcOpenShell 3D mesh face projection
and Shapely geometry operations.
Preserves original IFC GlobalIds, unit normalization, property sets, and source metadata.
Enforces strict zero-fabricated-geometry policy: failed shape extractions return empty
boundaries with explicit error/warning statuses instead of mock rectangles or convex hulls.
"""

import math
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

try:
    import ifcopenshell
    import ifcopenshell.geom as ifcopenshell_geom
    HAS_IFCOPENSHELL = True
    HAS_IFCOPENSHELL_GEOM = True
except ImportError:
    try:
        import ifcopenshell
        ifcopenshell_geom = None
        HAS_IFCOPENSHELL = True
        HAS_IFCOPENSHELL_GEOM = False
    except ImportError:
        ifcopenshell = None
        ifcopenshell_geom = None
        HAS_IFCOPENSHELL = False
        HAS_IFCOPENSHELL_GEOM = False

try:
    from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
    from shapely.ops import unary_union
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


class GeometryStatus(str, Enum):
    """Status of geometry extraction for a BIM entity."""
    VALID = "VALID"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class GeometryType(str, Enum):
    """Supported canonical 2D footprint geometry types."""
    POLYGON = "Polygon"
    MULTIPOLYGON = "MultiPolygon"


def shapely_to_geojson_coords(
    geom: Any, decimals: int = 4
) -> Tuple[str, Any, List[List[float]]]:
    """
    Convert a Shapely Polygon or MultiPolygon to (geometry_type, geometry_coordinates, boundary_vertices_compat).
    Preserves outer rings, holes (interior rings), and MultiPolygon components.
    """
    if geom.geom_type == "Polygon":
        ext_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in geom.exterior.coords]
        ext_compat = ext_coords[:-1] if (len(ext_coords) > 1 and ext_coords[0] == ext_coords[-1]) else ext_coords

        rings = [ext_coords]
        for interior in geom.interiors:
            hole_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in interior.coords]
            rings.append(hole_coords)

        return GeometryType.POLYGON.value, rings, ext_compat

    elif geom.geom_type == "MultiPolygon":
        multi_coords = []
        largest_compat: List[List[float]] = []
        max_area = -1.0

        for poly in geom.geoms:
            ext_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in poly.exterior.coords]
            ext_compat = ext_coords[:-1] if (len(ext_coords) > 1 and ext_coords[0] == ext_coords[-1]) else ext_coords
            if poly.area > max_area:
                max_area = poly.area
                largest_compat = ext_compat

            rings = [ext_coords]
            for interior in poly.interiors:
                hole_coords = [[round(p[0], decimals), round(p[1], decimals)] for p in interior.coords]
                rings.append(hole_coords)
            multi_coords.append(rings)

        return GeometryType.MULTIPOLYGON.value, multi_coords, largest_compat

    else:
        raise ValueError(f"Unsupported geometry type for 2D footprint: {geom.geom_type}")


def project_shape_to_2d_footprint(
    verts: Sequence[float],
    faces: Sequence[int],
    scale_to_meters: float = 1.0,
    decimals: int = 4,
) -> Tuple[Optional[str], Optional[Any], List[List[float]], GeometryStatus, Optional[str]]:
    """
    Authoritative 3D mesh face to 2D floor plan footprint projector.
    Projects 3D triangulated mesh faces from IfcOpenShell shape geometry to the 2D XY plane,
    filters degenerate zero-area projections, unions projected triangles using Shapely,
    and returns (geometry_type, geometry_coordinates, boundary_vertices, status, error).

    Preserves exact concavities, holes, and MultiPolygon components without reducing
    to a convex hull or inventing synthetic placement coordinates.
    """
    if not HAS_SHAPELY:
        return None, None, [], GeometryStatus.UNAVAILABLE, "IFC_SHAPELY_UNAVAILABLE: Shapely library is required for 2D geometry projection"

    if not verts or len(verts) < 9:
        return None, None, [], GeometryStatus.FAILED, "IFC_SHAPE_EMPTY_VERTICES: Less than 3 3D vertices returned by geometry engine"

    if not faces or len(faces) < 3:
        return None, None, [], GeometryStatus.FAILED, "IFC_SHAPE_EMPTY_FACES: No face indices returned by geometry engine"

    triangles = []
    num_verts = len(verts) // 3
    num_faces = len(faces)

    for i in range(0, num_faces, 3):
        if i + 2 >= num_faces:
            break
        v0, v1, v2 = faces[i], faces[i + 1], faces[i + 2]
        if v0 >= num_verts or v1 >= num_verts or v2 >= num_verts:
            continue

        x0, y0 = verts[v0 * 3] * scale_to_meters, verts[v0 * 3 + 1] * scale_to_meters
        x1, y1 = verts[v1 * 3] * scale_to_meters, verts[v1 * 3 + 1] * scale_to_meters
        x2, y2 = verts[v2 * 3] * scale_to_meters, verts[v2 * 3 + 1] * scale_to_meters

        if any(math.isnan(c) or math.isinf(c) for c in (x0, y0, x1, y1, x2, y2)):
            continue

        # 2D cross-product area check: 0.5 * abs(x0*(y1 - y2) + x1*(y2 - y0) + x2*(y0 - y1))
        area_2d_approx = 0.5 * abs(x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
        if area_2d_approx < 1e-7:
            # Skip degenerate projected triangles (e.g. vertical wall side faces)
            continue

        try:
            poly = Polygon([(x0, y0), (x1, y1), (x2, y2)])
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.is_empty and poly.area > 1e-7:
                triangles.append(poly)
        except Exception:
            continue

    if not triangles:
        return None, None, [], GeometryStatus.FAILED, "IFC_DEGENERATE_GEOMETRY: Projected faces yielded zero 2D area"

    try:
        unioned = unary_union(triangles)

        if not unioned.is_valid:
            unioned = unioned.buffer(0)

        if hasattr(unioned, "make_valid") and not unioned.is_valid:
            from shapely import make_valid
            unioned = make_valid(unioned)

        if unioned.geom_type == "GeometryCollection":
            polys = [g for g in unioned.geoms if g.geom_type in ("Polygon", "MultiPolygon") and g.area > 1e-6]
            if not polys:
                return None, None, [], GeometryStatus.FAILED, "IFC_DEGENERATE_GEOMETRY: GeometryCollection yielded no 2D polygons"
            unioned = unary_union(polys)

        if unioned.is_empty or unioned.area < 1e-6:
            return None, None, [], GeometryStatus.FAILED, "IFC_DEGENERATE_GEOMETRY: Unioned 2D footprint has effective zero area"

        geom_type, coords, boundary_compat = shapely_to_geojson_coords(unioned, decimals=decimals)
        return geom_type, coords, boundary_compat, GeometryStatus.VALID, None

    except Exception as exc:
        return None, None, [], GeometryStatus.FAILED, f"IFC_GEOMETRY_UNION_FAILED: {str(exc)}"


class ExtractedElement(BaseModel):
    """Extracted structural or spatial element from BIM model."""
    model_config = ConfigDict(extra="forbid")

    internal_id: str = Field(..., description="Internal element identifier")
    ifc_global_id: str = Field(..., description="IFC GlobalUniqueId (GlobalId)")
    global_id: str = Field(..., description="IFC GlobalUniqueId for backward compatibility")
    element_type: str = Field(..., description="IFC entity type (e.g., 'IfcWall', 'IfcDoor', 'IfcSpace')")
    name: str = Field(..., description="Element name or label")
    geometry_status: GeometryStatus = Field(default=GeometryStatus.VALID, description="Status of geometry extraction")
    geometry_type: Optional[str] = Field(default=None, description="Shapely/GeoJSON geometry type ('Polygon' or 'MultiPolygon')")
    geometry_coordinates: Optional[Any] = Field(default=None, description="GeoJSON-style coordinates structure (Polygon or MultiPolygon)")
    boundary_vertices: List[List[float]] = Field(default_factory=list, description="2D footprint exterior boundary vertices [[x0, y0], ...]")
    geometry_error: Optional[str] = Field(default=None, description="Error details if geometry extraction failed")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Extracted BIM properties")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Element provenance and unit metadata")


class IFCParsedFloorPlan(BaseModel):
    """Structured result returned by IFC ingestor."""
    model_config = ConfigDict(extra="forbid")

    file_name: str
    source_format: str = Field(default="IFC", description="IFC schema version (e.g. IFC4)")
    total_elements_count: int
    valid_geometry_count: int = Field(default=0, description="Count of elements with valid 2D geometry")
    failed_geometry_count: int = Field(default=0, description="Count of elements where geometry extraction failed")
    walls: List[ExtractedElement] = Field(default_factory=list)
    doors: List[ExtractedElement] = Field(default_factory=list)
    windows: List[ExtractedElement] = Field(default_factory=list)
    columns: List[ExtractedElement] = Field(default_factory=list)
    spaces: List[ExtractedElement] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Project & file level provenance metadata")
    extraction_warnings: List[str] = Field(default_factory=list, description="Non-fatal extraction warnings")


class IFCIngestor:
    """Ingestor parsing IFC 3D/2D files into canonical spatial structures using IfcOpenShell."""

    def parse_file(self, file_path_or_name: str) -> IFCParsedFloorPlan:
        """
        Parse an IFC file using IfcOpenShell and extract structural spatial elements.
        Never uses fake, mock, or fabricated placeholder geometry in production.
        """
        path = Path(file_path_or_name)

        if not path.exists():
            raise FileNotFoundError(f"IFC file not found at path: '{file_path_or_name}'")

        if not HAS_IFCOPENSHELL or ifcopenshell is None:
            raise ImportError(
                "IfcOpenShell library is not installed in the environment. "
                "Please install ifcopenshell to parse IFC files."
            )

        try:
            ifc_file = ifcopenshell.open(str(path))
        except Exception as exc:
            raise ValueError(f"Failed to open or parse IFC file '{path.name}': {str(exc)}") from exc

        return self._parse_with_ifcopenshell(ifc_file, path.name)

    def _parse_with_ifcopenshell(self, ifc_file: Any, file_name: str) -> IFCParsedFloorPlan:
        """Extract elements using native IfcOpenShell bindings."""
        unit_name, scale_to_meters = self._detect_length_unit_scale(ifc_file)
        project_meta = self._extract_project_metadata(ifc_file, file_name, unit_name, scale_to_meters)
        warnings: List[str] = []

        geom_settings = None
        if HAS_IFCOPENSHELL_GEOM and ifcopenshell_geom is not None:
            try:
                geom_settings = ifcopenshell_geom.settings()
                geom_settings.set(geom_settings.USE_WORLD_COORDINATES, True)
            except Exception as err:
                warnings.append(f"IfcOpenShell geometry settings warning: {str(err)}")

        # Query mandatory 5 element types (including IfcWallStandardCase)
        wall_entities = ifc_file.by_type("IfcWall") + ifc_file.by_type("IfcWallStandardCase")
        seen_wall_ids = set()
        dedup_walls = []
        for w in wall_entities:
            if w.id() not in seen_wall_ids:
                seen_wall_ids.add(w.id())
                dedup_walls.append(w)

        door_entities = ifc_file.by_type("IfcDoor")
        window_entities = ifc_file.by_type("IfcWindow")
        column_entities = ifc_file.by_type("IfcColumn")
        space_entities = ifc_file.by_type("IfcSpace")

        walls = [self._convert_ifc_entity(e, scale_to_meters, geom_settings, warnings, file_name) for e in dedup_walls]
        doors = [self._convert_ifc_entity(e, scale_to_meters, geom_settings, warnings, file_name) for e in door_entities]
        windows = [self._convert_ifc_entity(e, scale_to_meters, geom_settings, warnings, file_name) for e in window_entities]
        columns = [self._convert_ifc_entity(e, scale_to_meters, geom_settings, warnings, file_name) for e in column_entities]
        spaces = [self._convert_ifc_entity(e, scale_to_meters, geom_settings, warnings, file_name) for e in space_entities]

        all_elements = walls + doors + windows + columns + spaces

        # GlobalId uniqueness check across parsed source
        seen_guids = set()
        for elem in all_elements:
            if elem.ifc_global_id in seen_guids:
                warnings.append(f"DUPLICATE_GLOBAL_ID_DETECTED: Duplicate IFC GlobalId '{elem.ifc_global_id}' found in source.")
            else:
                seen_guids.add(elem.ifc_global_id)

        total = len(all_elements)
        valid_count = sum(1 for e in all_elements if e.geometry_status == GeometryStatus.VALID)
        failed_count = sum(1 for e in all_elements if e.geometry_status != GeometryStatus.VALID)

        return IFCParsedFloorPlan(
            file_name=file_name,
            source_format=project_meta.get("source_format", "IFC"),
            total_elements_count=total,
            valid_geometry_count=valid_count,
            failed_geometry_count=failed_count,
            walls=walls,
            doors=doors,
            windows=windows,
            columns=columns,
            spaces=spaces,
            source_metadata=project_meta,
            extraction_warnings=warnings,
        )

    def _convert_ifc_entity(
        self,
        entity: Any,
        scale_to_meters: float,
        geom_settings: Any,
        warnings: List[str],
        file_name: str,
    ) -> ExtractedElement:
        """Helper converting IfcOpenShell entity to ExtractedElement with real geometry or explicit failure status."""
        (
            geom_type,
            geom_coords,
            boundary,
            geom_status,
            geom_err,
            properties,
        ) = self._extract_entity_footprint_and_properties(
            entity, scale_to_meters, geom_settings, warnings
        )

        global_id = getattr(entity, "GlobalId", f"ifc_guid_{entity.id()}")
        name = getattr(entity, "Name", None) or entity.is_a()

        element_metadata = {
            "source_file": file_name,
            "ifc_id": entity.id(),
            "ifc_global_id": global_id,
        }

        return ExtractedElement(
            internal_id=f"{entity.is_a().lower()}_{entity.id()}",
            ifc_global_id=global_id,
            global_id=global_id,
            element_type=entity.is_a(),
            name=name,
            geometry_status=geom_status,
            geometry_type=geom_type,
            geometry_coordinates=geom_coords,
            boundary_vertices=boundary,
            geometry_error=geom_err,
            properties=properties,
            source_metadata=element_metadata,
        )

    def _extract_entity_footprint_and_properties(
        self,
        entity: Any,
        scale_to_meters: float,
        geom_settings: Any,
        warnings: List[str],
    ) -> Tuple[Optional[str], Optional[Any], List[List[float]], GeometryStatus, Optional[str], Dict[str, Any]]:
        """
        Extract real 2D boundary vertices (in meters) and properties for an IFC entity.
        NEVER fabricates fallback coordinates or placement rectangles if geometry is unavailable.
        """
        props: Dict[str, Any] = {}
        boundary: List[List[float]] = []
        geom_type: Optional[str] = None
        geom_coords: Optional[Any] = None
        geom_status: GeometryStatus = GeometryStatus.FAILED
        geom_err: Optional[str] = None

        global_id = getattr(entity, "GlobalId", "unknown")
        props["ifc_type"] = entity.is_a()
        props["tag"] = getattr(entity, "Tag", None)
        props["object_type"] = getattr(entity, "ObjectType", None)

        if hasattr(entity, "PredefinedType"):
            props["predefined_type"] = str(getattr(entity, "PredefinedType"))

        # Property set extraction
        try:
            if hasattr(ifcopenshell, "util") and hasattr(ifcopenshell.util, "element"):
                psets = ifcopenshell.util.element.get_psets(entity)
                if psets:
                    for pset_name, pset_dict in psets.items():
                        if isinstance(pset_dict, dict):
                            for k, v in pset_dict.items():
                                if k != "id" and v is not None:
                                    props[f"{pset_name}.{k}"] = (
                                        str(v) if not isinstance(v, (int, float, bool)) else v
                                    )
        except (AttributeError, KeyError, ValueError, TypeError) as pset_err:
            warnings.append(f"Property set extraction warning for GlobalId={global_id}: {str(pset_err)}")

        # Primary shape geometry extraction via IfcOpenShell shape engine & 3D face projection
        if geom_settings is not None and HAS_IFCOPENSHELL_GEOM and ifcopenshell_geom is not None:
            try:
                shape = ifcopenshell_geom.create_shape(geom_settings, entity)
                verts = shape.geometry.verts
                faces = shape.geometry.faces

                g_type, g_coords, b_verts, g_status, g_err = project_shape_to_2d_footprint(
                    verts=verts,
                    faces=faces,
                    scale_to_meters=scale_to_meters,
                    decimals=4,
                )
                geom_type = g_type
                geom_coords = g_coords
                boundary = b_verts
                geom_status = g_status
                geom_err = g_err

            except Exception as shape_err:
                geom_status = GeometryStatus.FAILED
                geom_err = f"IFC_SHAPE_CREATION_FAILED: {str(shape_err)}"
                warnings.append(
                    f"Shape creation warning for {entity.is_a()} GlobalId={global_id}: {str(shape_err)}"
                )
        else:
            geom_status = GeometryStatus.FAILED
            geom_err = "IFC_GEOM_ENGINE_UNAVAILABLE: IfcOpenShell geometry creation module unavailable"

        # Strict zero-fabricated-geometry enforcement:
        if geom_status != GeometryStatus.VALID:
            geom_type = None
            geom_coords = None
            boundary = []
            if not geom_err:
                geom_err = "IFC_GEOMETRY_UNAVAILABLE"

        return geom_type, geom_coords, boundary, geom_status, geom_err, props

    def _detect_length_unit_scale(self, ifc_file: Any) -> Tuple[str, float]:
        """
        Detect declared length unit system and unit scale factor to meters.
        Prefers ifcopenshell.util.unit.calculate_unit_scale when supported.
        """
        unit_name = "METRE"
        scale_to_meters = 1.0

        # Try standard IfcOpenShell unit utility
        try:
            import ifcopenshell.util.unit
            scale = ifcopenshell.util.unit.calculate_unit_scale(ifc_file)
            if scale is not None and float(scale) > 0:
                scale_to_meters = float(scale)
        except (ImportError, AttributeError, ValueError, TypeError):
            pass

        try:
            projects = ifc_file.by_type("IfcProject")
            if projects:
                project = projects[0]
                units_in_context = getattr(project, "UnitsInContext", None)
                if units_in_context:
                    units = getattr(units_in_context, "Units", [])
                    for unit in units:
                        unit_type = getattr(unit, "UnitType", None)
                        if unit_type == "LENGTHUNIT":
                            if unit.is_a("IfcSIUnit"):
                                prefix = getattr(unit, "Prefix", None)
                                name = getattr(unit, "Name", "METRE")
                                unit_name = str(name).upper()
                                if scale_to_meters == 1.0:
                                    if prefix == "MILLI":
                                        scale_to_meters = 0.001
                                    elif prefix == "CENTI":
                                        scale_to_meters = 0.01
                                    elif prefix == "KILO":
                                        scale_to_meters = 1000.0
                                    elif name == "METRE":
                                        scale_to_meters = 1.0
                            elif unit.is_a("IfcConversionBasedUnit"):
                                name = getattr(unit, "Name", "FOOT")
                                unit_name = str(name).upper()
                                if scale_to_meters == 1.0:
                                    conv = getattr(unit, "ConversionFactor", None)
                                    if conv:
                                        val_comp = getattr(conv, "ValueComponent", None)
                                        if val_comp:
                                            val = getattr(val_comp, "wrappedValue", None)
                                            if val is not None:
                                                scale_to_meters = float(val)
        except (AttributeError, KeyError, ValueError, TypeError):
            pass

        if abs(scale_to_meters - 0.3048) < 1e-4 and unit_name == "METRE":
            unit_name = "FOOT"

        return unit_name, scale_to_meters

    def _extract_project_metadata(
        self, ifc_file: Any, file_name: str, unit_name: str, scale_to_meters: float
    ) -> Dict[str, Any]:
        """Extract project, building, site, map conversion, CRS, and header metadata."""
        meta: Dict[str, Any] = {
            "file_name": file_name,
            "source_format": getattr(ifc_file, "schema", "IFC"),
            "declared_length_unit": unit_name,
            "unit_scale_to_meters": scale_to_meters,
            "normalized_coordinate_unit": "metre",
            "project_name": None,
            "building_name": None,
            "header_description": None,
            "header_timestamp": None,
            "exporter_application": None,
            "map_conversion": "UNAVAILABLE",
            "projected_crs": "UNAVAILABLE",
        }

        try:
            if hasattr(ifc_file, "header"):
                header = ifc_file.header
                if hasattr(header, "file_description") and hasattr(header.file_description, "description"):
                    desc = header.file_description.description
                    meta["header_description"] = desc[0] if isinstance(desc, (list, tuple)) and desc else str(desc)
                if hasattr(header, "file_name"):
                    fn = header.file_name
                    if hasattr(fn, "time_stamp"):
                        meta["header_timestamp"] = str(fn.time_stamp)
                    if hasattr(fn, "originating_system"):
                        meta["exporter_application"] = str(fn.originating_system)

            projects = ifc_file.by_type("IfcProject")
            if projects:
                meta["project_name"] = getattr(projects[0], "Name", None)

            buildings = ifc_file.by_type("IfcBuilding")
            if buildings:
                meta["building_name"] = getattr(buildings[0], "Name", None)

            map_conversions = ifc_file.by_type("IfcMapConversion") if hasattr(ifc_file, "by_type") else []
            if map_conversions:
                mc = map_conversions[0]
                meta["map_conversion"] = {
                    "eastings": getattr(mc, "Eastings", None),
                    "northings": getattr(mc, "Northings", None),
                    "orthogonal_height": getattr(mc, "OrthogonalHeight", None),
                    "scale": getattr(mc, "Scale", None),
                }

            projected_crs = ifc_file.by_type("IfcProjectedCRS") if hasattr(ifc_file, "by_type") else []
            if projected_crs:
                crs = projected_crs[0]
                meta["projected_crs"] = {
                    "name": getattr(crs, "Name", None),
                    "geodetic_datum": getattr(crs, "GeodeticDatum", None),
                }

        except (AttributeError, KeyError, ValueError, TypeError):
            pass

        return meta

