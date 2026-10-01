"""
Revit IFC (Industry Foundation Classes) Floor Plan Ingestion Engine.
Extracts structural elements (IfcWall, IfcDoor, IfcWindow, IfcColumn, IfcSpace)
and calculates 2D footprint polygon geometry using IfcOpenShell and Shapely.
Preserves original IFC GlobalIds, unit normalization, property sets, and source metadata.
Enforces strict zero-fabricated-geometry policy: failed shape extractions return empty
boundaries with explicit error/warning statuses instead of mock rectangles.
"""

import math
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
    from shapely.geometry import MultiPoint, Polygon
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


class GeometryStatus(str, Enum):
    """Status of geometry extraction for a BIM entity."""
    VALID = "VALID"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class ExtractedElement(BaseModel):
    """Extracted structural or spatial element from BIM model."""
    model_config = ConfigDict(extra="forbid")

    internal_id: str = Field(..., description="Internal element identifier")
    ifc_global_id: str = Field(..., description="IFC GlobalUniqueId (GlobalId)")
    global_id: str = Field(..., description="IFC GlobalUniqueId for backward compatibility")
    element_type: str = Field(..., description="IFC entity type (e.g., 'IfcWall', 'IfcDoor', 'IfcSpace')")
    name: str = Field(..., description="Element name or label")
    geometry_status: GeometryStatus = Field(default=GeometryStatus.VALID, description="Status of geometry extraction")
    boundary_vertices: List[List[float]] = Field(default_factory=list, description="2D footprint vertices [[x0, y0], ...]")
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
        boundary, geom_status, geom_err, properties = self._extract_entity_footprint_and_properties(
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
    ) -> Tuple[List[List[float]], GeometryStatus, Optional[str], Dict[str, Any]]:
        """
        Extract real 2D boundary vertices (in meters) and properties for an IFC entity.
        NEVER fabricates fallback coordinates or placement rectangles if geometry is unavailable.
        """
        props: Dict[str, Any] = {}
        boundary: List[List[float]] = []
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
        except Exception as pset_err:
            warnings.append(f"Property set extraction warning for GlobalId={global_id}: {str(pset_err)}")

        # Primary shape geometry extraction via IfcOpenShell shape engine
        if geom_settings is not None and HAS_IFCOPENSHELL_GEOM and ifcopenshell_geom is not None:
            try:
                shape = ifcopenshell_geom.create_shape(geom_settings, entity)
                verts = shape.geometry.verts
                if verts and len(verts) >= 6:
                    pts_2d = []
                    for i in range(0, len(verts), 3):
                        x = verts[i] * scale_to_meters
                        y = verts[i + 1] * scale_to_meters
                        if not math.isnan(x) and not math.isnan(y) and not math.isinf(x) and not math.isinf(y):
                            pts_2d.append((x, y))

                    if HAS_SHAPELY and len(pts_2d) >= 3:
                        mp = MultiPoint(pts_2d)
                        hull = mp.convex_hull
                        if isinstance(hull, Polygon) and not hull.is_empty and hull.area > 1e-6:
                            coords = list(hull.exterior.coords)
                            if coords and len(coords) > 1 and coords[0] == coords[-1]:
                                coords = coords[:-1]
                            boundary = [[round(p[0], 4), round(p[1], 4)] for p in coords]
                            geom_status = GeometryStatus.VALID
                        elif hasattr(hull, "bounds"):
                            minx, miny, maxx, maxy = hull.bounds
                            if (maxx - minx) > 1e-4 or (maxy - miny) > 1e-4:
                                boundary = [
                                    [round(minx, 4), round(miny, 4)],
                                    [round(maxx, 4), round(miny, 4)],
                                    [round(maxx, 4), round(maxy, 4)],
                                    [round(minx, 4), round(maxy, 4)],
                                ]
                                geom_status = GeometryStatus.VALID
                            else:
                                geom_err = "IFC_DEGENERATE_GEOMETRY: Vertices yielded zero-area 2D footprint"
                        else:
                            geom_err = "IFC_GEOMETRY_CONVEX_HULL_FAILED: Unable to construct valid 2D polygon"
                    elif len(pts_2d) >= 3:
                        xs = [p[0] for p in pts_2d]
                        ys = [p[1] for p in pts_2d]
                        minx, maxx = min(xs), max(xs)
                        miny, maxy = min(ys), max(ys)
                        if (maxx - minx) > 1e-4 or (maxy - miny) > 1e-4:
                            boundary = [
                                [round(minx, 4), round(miny, 4)],
                                [round(maxx, 4), round(miny, 4)],
                                [round(maxx, 4), round(maxy, 4)],
                                [round(minx, 4), round(maxy, 4)],
                            ]
                            geom_status = GeometryStatus.VALID
                        else:
                            geom_err = "IFC_DEGENERATE_GEOMETRY: Vertices yielded zero-area 2D footprint"
                    else:
                        geom_err = "IFC_INSUFFICIENT_VERTICES: Less than 3 valid 2D vertices extracted"
                else:
                    geom_err = "IFC_SHAPE_EMPTY_VERTICES: No 3D vertices returned by geometry engine"
            except Exception as shape_err:
                geom_err = f"IFC_SHAPE_CREATION_FAILED: {str(shape_err)}"
                warnings.append(
                    f"Shape creation warning for {entity.is_a()} GlobalId={global_id}: {str(shape_err)}"
                )
        else:
            geom_err = "IFC_GEOM_ENGINE_UNAVAILABLE: IfcOpenShell geometry creation module unavailable"

        # Strict zero-fabricated-geometry enforcement:
        # If geometry is not valid, boundary must be empty [] and status must be FAILED/UNAVAILABLE.
        if geom_status != GeometryStatus.VALID:
            boundary = []
            if not geom_err:
                geom_err = "IFC_GEOMETRY_UNAVAILABLE"

        return boundary, geom_status, geom_err, props

    def _detect_length_unit_scale(self, ifc_file: Any) -> Tuple[str, float]:
        """Detect declared length unit system and unit scale factor to meters."""
        unit_name = "METRE"
        scale_to_meters = 1.0

        try:
            projects = ifc_file.by_type("IfcProject")
            if not projects:
                return unit_name, scale_to_meters

            project = projects[0]
            units_in_context = getattr(project, "UnitsInContext", None)
            if not units_in_context:
                return unit_name, scale_to_meters

            units = getattr(units_in_context, "Units", [])
            for unit in units:
                unit_type = getattr(unit, "UnitType", None)
                if unit_type == "LENGTHUNIT":
                    if unit.is_a("IfcSIUnit"):
                        prefix = getattr(unit, "Prefix", None)
                        name = getattr(unit, "Name", "METRE")
                        unit_name = str(name).upper()
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
                        conv = getattr(unit, "ConversionFactor", None)
                        if conv:
                            val_comp = getattr(conv, "ValueComponent", None)
                            if val_comp:
                                val = getattr(val_comp, "wrappedValue", None)
                                if val is not None:
                                    scale_to_meters = float(val)
        except Exception:
            pass

        return unit_name, scale_to_meters

    def _extract_project_metadata(
        self, ifc_file: Any, file_name: str, unit_name: str, scale_to_meters: float
    ) -> Dict[str, Any]:
        """Extract project, building, site, and header metadata."""
        meta: Dict[str, Any] = {
            "file_name": file_name,
            "source_format": getattr(ifc_file, "schema", "IFC"),
            "declared_length_unit": unit_name,
            "unit_scale_to_meters": scale_to_meters,
            "project_name": None,
            "building_name": None,
            "header_description": None,
            "header_timestamp": None,
            "exporter_application": None,
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
        except Exception:
            pass

        return meta
