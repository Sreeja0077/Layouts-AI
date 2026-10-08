"""
Unit & Integration test for Revit IFC floor plan ingestion engine (Task 2.1).
Verifies real IFC parsing using IfcOpenShell on fixture "docs/4420 Ashland Rev 2.ifc".
Proves actual 2D geometry extraction from 3D mesh face projection, concavity preservation,
holes and MultiPolygon topology, GlobalId preservation, unit normalization,
and strict zero-fabricated-geometry enforcement.
"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from shapely.geometry import MultiPolygon, Polygon

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.ifc_ingest import (
    IFCIngestor,
    IFCParsedFloorPlan,
    ExtractedElement,
    Geometry2D,
    GeometryStatus,
    GeometryType,
    project_shape_to_2d_footprint,
)

ROOT_DIR = BACKEND_DIR.parent
REAL_IFC_FILE = ROOT_DIR / "docs" / "4420 Ashland Rev 2.ifc"


def test_concave_l_shape_mesh_projection():
    """
    Focused Unit Test for Mesh Projection Helper:
    Verifies that an L-shaped 3D mesh is projected into an exact concave 2D Polygon,
    and is NOT reduced to a rectangular convex hull.
    """
    # 2D L-shape vertices in XY:
    # (0,0), (4,0), (4,2), (2,2), (2,6), (0,6)
    # Inward concave corner is at (2,2).
    # Area of L-shape = 4*2 + 2*4 = 16.0.
    # Bounding box area = 4*6 = 24.0.
    verts_2d = [
        (0.0, 0.0),  # 0
        (4.0, 0.0),  # 1
        (4.0, 2.0),  # 2
        (2.0, 2.0),  # 3 (inward corner)
        (2.0, 6.0),  # 4
        (0.0, 6.0),  # 5
    ]

    # Create 3D mesh extruded in Z from Z=0 to Z=3
    verts_3d = []
    for x, y in verts_2d:
        verts_3d.extend([x, y, 0.0])
    for x, y in verts_2d:
        verts_3d.extend([x, y, 3.0])

    faces = [
        # Top face triangles
        6, 7, 8,
        6, 8, 9,
        6, 9, 10,
        6, 10, 11,
        # Bottom face triangles (0..5)
        0, 1, 2,
        0, 2, 3,
        0, 3, 4,
        0, 4, 5,
        # Side wall vertical triangles (project to zero area 2D lines)
        0, 1, 7,  0, 7, 6,
        1, 2, 8,  1, 8, 7,
        2, 3, 9,  2, 9, 8,
        3, 4, 10, 3, 10, 9,
        4, 5, 11, 4, 11, 10,
        5, 0, 6,  5, 6, 11,
    ]

    geom_type, geom_coords, boundary_compat, status, err = project_shape_to_2d_footprint(
        verts=verts_3d,
        faces=faces,
        scale_to_meters=1.0,
    )

    assert status == GeometryStatus.VALID, f"Projection failed: {err}"
    assert geom_type == GeometryType.POLYGON
    assert geom_coords is not None

    poly = Polygon(boundary_compat)
    assert poly.is_valid
    assert abs(poly.area - 16.0) < 1e-3, f"Expected L-shape area 16.0, got {poly.area}"

    # Verify concavity: convex hull area is 20.0, bounding box area is 24.0, while actual poly area is 16.0!
    hull = poly.convex_hull
    assert abs(hull.area - 20.0) < 1e-3, f"Convex hull area should be 20.0, got {hull.area}"
    minx, miny, maxx, maxy = poly.bounds
    bbox_area = (maxx - minx) * (maxy - miny)
    assert abs(bbox_area - 24.0) < 1e-3, f"Bounding box area should be 24.0, got {bbox_area}"
    assert poly.area < hull.area < bbox_area, "Concave geometry area (16.0) MUST be less than convex hull (20.0) and bounding box (24.0)!"


    # Verify inward corner (2.0, 2.0) is preserved in boundary
    has_inward_corner = any(abs(v[0] - 2.0) < 1e-3 and abs(v[1] - 2.0) < 1e-3 for v in boundary_compat)
    assert has_inward_corner, "Inward concave corner (2.0, 2.0) missing from projected boundary!"

    print("CONCAVE L-SHAPE MESH PROJECTION TEST PASSED: Concavity retained!")


def test_multipart_and_hole_mesh_projection():
    """
    Focused Unit Test for Multipart & Hole Footprint Projections:
    Proves that disconnected mesh faces result in MultiPolygon (with boundary_vertices = [])
    and hollow meshes produce interior holes.
    """
    # 1. Disconnected Components -> MultiPolygon
    verts_disjoint = [
        0,0,0, 1,0,0, 1,1,0, 0,1,0,  # Square 1 (indices 0..3)
        5,5,0, 6,5,0, 6,6,0, 5,6,0,  # Square 2 (indices 4..7)
    ]
    faces_disjoint = [
        0, 1, 2, 0, 2, 3,  # Square 1 triangles
        4, 5, 6, 4, 6, 7,  # Square 2 triangles
    ]

    geom_type, geom_coords, boundary_compat, status, err = project_shape_to_2d_footprint(
        verts=verts_disjoint,
        faces=faces_disjoint,
        scale_to_meters=1.0,
    )

    assert status == GeometryStatus.VALID, f"Disjoint projection failed: {err}"
    assert geom_type == GeometryType.MULTIPOLYGON
    assert isinstance(geom_coords, list) and len(geom_coords) == 2, "MultiPolygon coords must contain 2 component polygons"
    assert boundary_compat == [], "MultiPolygon MUST return empty boundary_vertices [] to prevent lossy non-authoritative representations"

    # 2. Polygon with interior hole
    verts_ring = [
        # Outer square (0..3)
        0,0,0, 4,0,0, 4,4,0, 0,4,0,
        # Inner square (4..7)
        1,1,0, 3,1,0, 3,3,0, 1,3,0,
    ]
    faces_ring = [
        # Bottom slab (0, 1, 5, 4)
        0, 1, 5, 0, 5, 4,
        # Right slab (1, 2, 6, 5)
        1, 2, 6, 1, 6, 5,
        # Top slab (2, 3, 7, 6)
        2, 3, 7, 2, 7, 6,
        # Left slab (3, 0, 4, 7)
        3, 0, 4, 3, 4, 7,
    ]

    geom_type, geom_coords, boundary_compat, status, err = project_shape_to_2d_footprint(
        verts=verts_ring,
        faces=faces_ring,
        scale_to_meters=1.0,
    )

    assert status == GeometryStatus.VALID, f"Hole projection failed: {err}"
    assert geom_type == GeometryType.POLYGON
    assert isinstance(geom_coords, list) and len(geom_coords) == 2, "Polygon coords with hole must contain outer ring and 1 interior hole ring"
    assert boundary_compat == [], "Polygon with holes MUST return empty boundary_vertices [] to prevent lossy non-authoritative representations"

    print("MULTIPART AND HOLE MESH PROJECTION TEST PASSED: MultiPolygon and interior holes preserved!")


def test_real_ifc_ingest_parsing():
    """Verify parsing real .ifc file with IfcOpenShell and extracting all 5 mandatory element types."""
    assert REAL_IFC_FILE.exists(), f"Real IFC fixture file missing at {REAL_IFC_FILE}"

    ingestor = IFCIngestor()
    result: IFCParsedFloorPlan = ingestor.parse_file(str(REAL_IFC_FILE))

    print(f"\n[Real IFC Ingestion Test] File: {result.file_name}")
    print(f"[Real IFC Ingestion Test] Total Elements Extracted: {result.total_elements_count}")
    print(f"[Real IFC Ingestion Test] Valid Geometry Count: {result.valid_geometry_count}")
    print(f"[Real IFC Ingestion Test] Failed Geometry Count: {result.failed_geometry_count}")
    print(f"[Real IFC Ingestion Test] Walls: {len(result.walls)}")
    print(f"[Real IFC Ingestion Test] Doors: {len(result.doors)}")
    print(f"[Real IFC Ingestion Test] Windows: {len(result.windows)}")
    print(f"[Real IFC Ingestion Test] Columns: {len(result.columns)}")
    print(f"[Real IFC Ingestion Test] Spaces: {len(result.spaces)}")
    print(f"[Real IFC Ingestion Test] Declared Unit: {result.source_metadata.get('declared_length_unit')}")
    print(f"[Real IFC Ingestion Test] Scale Factor to Meters: {result.source_metadata.get('unit_scale_to_meters')}")

    # 1. Total elements and counts
    assert result.total_elements_count == 420, f"Expected 420 elements, got {result.total_elements_count}"
    assert result.valid_geometry_count > 0, "No valid geometries extracted!"
    assert len(result.walls) == 225
    assert len(result.doors) == 21
    assert len(result.windows) == 30
    assert len(result.columns) == 18
    assert len(result.spaces) == 12
    assert len(result.furniture) == 114, f"Expected 114 furniture items, got {len(result.furniture)}"

    # 2. Verify element GlobalIds, geometry status, typed Geometry2D, and boundaries
    all_elements = result.walls + result.doors + result.windows + result.columns + result.spaces + result.furniture
    valid_wall_areas = []

    for elem in all_elements:
        assert elem.ifc_global_id and len(elem.ifc_global_id) > 0, f"Element {elem.internal_id} missing ifc_global_id!"
        assert elem.global_id == elem.ifc_global_id, "global_id and ifc_global_id mismatch!"
        assert elem.element_type and elem.element_type.startswith("Ifc"), f"Invalid element_type {elem.element_type}"
        assert elem.internal_id.startswith(elem.element_type.lower()), f"Invalid internal_id {elem.internal_id}"
        assert elem.name not in ("Polygon", "MultiPolygon"), f"Placeholder name '{elem.name}' found on {elem.ifc_global_id}"
        assert hasattr(elem, "category") and len(elem.category) > 0
        assert hasattr(elem, "subtype") and len(elem.subtype) > 0

        if elem.geometry_status == GeometryStatus.VALID:
            assert elem.geometry_type in (GeometryType.POLYGON, GeometryType.MULTIPOLYGON)
            assert elem.geometry_coordinates is not None
            assert elem.geometry is not None
            assert elem.geometry.type == elem.geometry_type
            assert elem.geometry.coordinates == elem.geometry_coordinates

            if elem.geometry_type == GeometryType.POLYGON and len(elem.boundary_vertices) >= 3:
                poly = Polygon(elem.boundary_vertices)
                assert poly.area > 0.0, f"Valid geometry for {elem.ifc_global_id} produced zero-area polygon!"
                if elem.element_type in ["IfcWall", "IfcWallStandardCase"]:
                    valid_wall_areas.append(poly.area)
        else:
            # Failed geometry elements MUST have empty boundary_vertices []
            assert elem.boundary_vertices == [], f"Failed element {elem.ifc_global_id} must have empty boundary_vertices!"
            assert elem.geometry_type is None
            assert elem.geometry_coordinates is None
            assert elem.geometry is None
            assert elem.geometry_error is not None, f"Failed element {elem.ifc_global_id} missing geometry_error!"

    # 3. Quantitative metrics check across walls
    assert len(valid_wall_areas) > 0
    unique_areas = set(round(a, 3) for a in valid_wall_areas)
    assert len(unique_areas) > 1, "Expected distinct wall footprint areas across real IFC walls!"

    # 4. Source metadata verification
    assert result.source_metadata.get("declared_length_unit") == "FOOT"
    assert result.source_metadata.get("unit_scale_to_meters") == 0.3048
    assert result.file_name == REAL_IFC_FILE.name
    assert result.source_metadata.get("exporter_application") is not None

    # 5. IfcOpenShell shape vertices must be retained in SI metres exactly once.
    # The fixture contains a wall with a ~25 ft longitudinal footprint, which should
    # therefore be ~7.62 m after geometry processing, not ~2.32 m (double-scaled).
    first_valid_wall = next(
        wall
        for wall in result.walls
        if wall.geometry_status == GeometryStatus.VALID
        and wall.geometry_type == GeometryType.POLYGON
        and len(wall.boundary_vertices) >= 3
    )
    first_wall_poly = Polygon(first_valid_wall.boundary_vertices)
    wall_span = max(
        first_wall_poly.bounds[2] - first_wall_poly.bounds[0],
        first_wall_poly.bounds[3] - first_wall_poly.bounds[1],
    )
    assert wall_span > 7.0, (
        f"IFC geometry appears to have been scaled twice: expected a wall span > 7m, got {wall_span:.3f}m"
    )

    # 6. IFC entities expose building-storey metadata for floor-specific rendering.
    space_storeys = {
        (space.properties or {}).get("storey_name")
        for space in result.spaces
        if space.geometry_status == GeometryStatus.VALID
    }
    space_storeys.discard(None)
    assert space_storeys, "Valid IFC spaces must retain storey_name metadata"
    assert "First Floor" in space_storeys
    assert "Second Floor" in space_storeys

    print(f"REAL IFC FILE PARSING VERIFIED: {result.valid_geometry_count} valid elements, {len(result.furniture)} furniture items, {len(unique_areas)} distinct wall areas.")


def test_pydantic_serialization():
    """
    Verify clean Pydantic JSON serialization:
    Calls model_dump() and model_dump_json() and asserts JSON validity.
    """
    ingestor = IFCIngestor()
    result = ingestor.parse_file(str(REAL_IFC_FILE))

    dump_dict = result.model_dump()
    assert dump_dict["total_elements_count"] == 420
    assert len(dump_dict["furniture"]) == 114

    json_str = result.model_dump_json()
    assert isinstance(json_str, str) and len(json_str) > 1000

    parsed_back = json.loads(json_str)
    assert parsed_back["file_name"] == REAL_IFC_FILE.name
    assert len(parsed_back["walls"]) == 225
    assert len(parsed_back["furniture"]) == 114

    # Inspect first wall's typed geometry container in JSON
    wall_json = parsed_back["walls"][0]
    assert wall_json["geometry_status"] == "VALID"
    assert wall_json["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert isinstance(wall_json["geometry"]["coordinates"], list)

    print("PYDANTIC JSON SERIALIZATION TEST PASSED: Clean JSON serialization verified!")


def test_furniture_item_extraction_and_subtype_preservation():
    """
    Focused Unit Test for Unified Furniture / Items Extraction & Subtype Preservation:
    Verifies that furniture items are extracted into IFCParsedFloorPlan.furniture,
    preserve GlobalId, element_type, name, category, subtype, and actual geometry.
    """
    ingestor = IFCIngestor()
    result = ingestor.parse_file(str(REAL_IFC_FILE))

    assert hasattr(result, "furniture"), "IFCParsedFloorPlan missing furniture field!"
    assert len(result.furniture) == 114, f"Expected 114 furniture items, got {len(result.furniture)}"

    subtypes_found = set()
    for item in result.furniture:
        assert item.category == "FURNITURE_ITEM", f"Expected category FURNITURE_ITEM, got {item.category}"
        assert item.ifc_global_id and len(item.ifc_global_id) > 0
        assert item.element_type and len(item.element_type) > 0
        assert item.name not in ("Polygon", "MultiPolygon"), f"Placeholder name found: {item.name}"
        subtypes_found.add(item.subtype)

    print(f"FURNITURE SUBTYPES EXTRACTED: {subtypes_found}")
    assert len(subtypes_found) > 0, "No furniture subtypes derived!"


def test_forced_geometry_failure_regression(monkeypatch=None):
    """
    Mandatory Regression Test:
    Forces IfcOpenShell shape generation to fail for an element and verifies:
    1. The parser does NOT create a fake rectangle or placement fallback.
    2. boundary_vertices is empty [].
    3. geometry_status is FAILED.
    4. geometry_error is populated with error details.
    5. extraction_warnings contains the warning.
    6. Element retains internal_id and ifc_global_id.
    """
    import app.bim.ifc_ingest as ifc_mod

    def mock_create_shape(settings, entity):
        raise RuntimeError("Simulated geometry engine crash for regression test")

    original_create_shape = getattr(ifc_mod.ifcopenshell_geom, "create_shape", None)

    try:
        if monkeypatch is not None:
            if ifc_mod.HAS_IFCOPENSHELL_GEOM and ifc_mod.ifcopenshell_geom is not None:
                monkeypatch.setattr(ifc_mod.ifcopenshell_geom, "create_shape", mock_create_shape)
        elif ifc_mod.HAS_IFCOPENSHELL_GEOM and ifc_mod.ifcopenshell_geom is not None:
            ifc_mod.ifcopenshell_geom.create_shape = mock_create_shape

        ingestor = IFCIngestor()
        result = ingestor.parse_file(str(REAL_IFC_FILE))

        assert result.total_elements_count == 420
        assert result.valid_geometry_count == 0, "All geometry extractions should fail when shape creation crashes!"
        assert result.failed_geometry_count == 420
        assert len(result.extraction_warnings) > 0

        wall = result.walls[0]
        assert wall.geometry_status == GeometryStatus.FAILED
        assert wall.boundary_vertices == [], "Forced failure MUST result in empty boundary_vertices [], never a fake rectangle!"
        assert wall.geometry_type is None
        assert wall.geometry_coordinates is None
        assert wall.geometry is None
        assert wall.geometry_error is not None
        assert "IFC_SHAPE_CREATION_FAILED" in wall.geometry_error
        assert wall.ifc_global_id and len(wall.ifc_global_id) > 0
        assert wall.internal_id.startswith("ifcwall")

        print("FORCED GEOMETRY FAILURE REGRESSION TEST PASSED: Zero fake geometry created!")

    finally:
        if monkeypatch is None and ifc_mod.HAS_IFCOPENSHELL_GEOM and ifc_mod.ifcopenshell_geom is not None and original_create_shape is not None:
            ifc_mod.ifcopenshell_geom.create_shape = original_create_shape



def test_repeated_ifc_parsing_and_no_retained_references():
    """
    Focused Regression Test:
    Parses the real IFC fixture multiple times sequentially in one process.
    Verifies identical element counts, geometry status, and that no retained
    IfcOpenShell file/entity object references survive in returned models.
    """
    ingestor = IFCIngestor()

    for i in range(3):
        result = ingestor.parse_file(str(REAL_IFC_FILE))

        assert result.total_elements_count == 420
        assert result.valid_geometry_count == 418
        assert result.failed_geometry_count == 2
        assert len(result.walls) == 225
        assert len(result.doors) == 21
        assert len(result.windows) == 30
        assert len(result.columns) == 18
        assert len(result.spaces) == 12
        assert len(result.furniture) == 114

        # Verify returned data contains no raw IfcOpenShell or C++ instances
        all_elements = result.walls + result.doors + result.windows + result.columns + result.spaces
        for elem in all_elements:
            for val in list(elem.properties.values()) + list(elem.source_metadata.values()):
                assert not str(type(val)).startswith("<class 'ifcopenshell"), f"Retained IfcOpenShell object reference found: {type(val)}"

    print("REPEATED PARSING REGRESSION TEST PASSED: 3 sequential parses clean with zero retained references!")


def test_missing_file_raises_explicit_error():
    """Verify that a missing file path raises explicit FileNotFoundError."""
    ingestor = IFCIngestor()
    with pytest.raises(FileNotFoundError) as exc_info:
        ingestor.parse_file("non_existent_file_path_12345.ifc")
    assert "IFC file not found" in str(exc_info.value)
    print("VERIFIED EXPLICIT FileNotFoundError FOR MISSING FILE!")


def test_malformed_file_raises_explicit_error():
    """Verify that a malformed IFC file raises explicit ValueError."""
    ingestor = IFCIngestor()
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False, mode="w") as tmp:
        tmp.write("NOT_A_VALID_IFC_HEADER_DATA_12345")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError) as exc_info:
            ingestor.parse_file(tmp_path)
        assert "Failed to open or parse IFC file" in str(exc_info.value)
        print("VERIFIED EXPLICIT ValueError FOR MALFORMED FILE!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_semantic_subtype_classification():
    """
    Unit Test for Phase 1 Semantic Subtype Classification:
    Verifies that derive_semantic_category_and_subtype accurately classifies:
    - Standard vs Garage/Overhead/Rolling Doors
    - Desks, Conference Tables, Chairs, Sectionals, Pantry Counters, Toilets, Sinks
    """
    from app.bim.ifc_ingest import derive_semantic_category_and_subtype

    class MockEntity:
        def __init__(self, ifc_type, name="", obj_type="", predef_type="", tag=""):
            self._type = ifc_type
            self.Name = name
            self.ObjectType = obj_type
            self.PredefinedType = predef_type
            self.Tag = tag

        def is_a(self):
            return self._type

    # Door Subtypes
    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcDoor", name="Overhead Sectional Garage Door"))
    assert cat == "DOOR" and sub in ("GARAGE_DOOR", "OVERHEAD_DOOR")

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcDoor", name="Rolling Security Shutter Door"))
    assert cat == "DOOR" and sub == "ROLLING_DOOR"

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcDoor", name="Single-Flush Interior Door"))
    assert cat == "DOOR" and sub == "STANDARD_DOOR"

    # Furniture / Fixtures
    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcFurnishingElement", name="Boardroom Conference Table"))
    assert cat == "FURNITURE_ITEM" and sub == "CONFERENCE_TABLE"

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcFurnishingElement", name="Executive L-Desk"))
    assert cat == "FURNITURE_ITEM" and sub == "DESK"

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcFurnishingElement", name="Ergonomic Swivel Task Chair"))
    assert cat == "FURNITURE_ITEM" and sub == "CHAIR"

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcFurnishingElement", name="Modern L-Sectional Sofa"))
    assert cat == "FURNITURE_ITEM" and sub in ("SOFA", "SECTIONAL")

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcSanitaryTerminal", name="Wall-Hung Toilet Bowl"))
    assert cat == "FURNITURE_ITEM" and sub == "TOILET"

    cat, sub = derive_semantic_category_and_subtype(MockEntity("IfcSanitaryTerminal", name="Vanity Wash Basin"))
    assert cat == "FURNITURE_ITEM" and sub == "BASIN"

    print("SEMANTIC SUBTYPE CLASSIFICATION TEST PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_concave_l_shape_mesh_projection()
    test_multipart_and_hole_mesh_projection()
    test_real_ifc_ingest_parsing()
    test_pydantic_serialization()
    test_repeated_ifc_parsing_and_no_retained_references()
    test_forced_geometry_failure_regression()
    test_missing_file_raises_explicit_error()
    test_malformed_file_raises_explicit_error()
    test_semantic_subtype_classification()
    print("\nALL REVIT IFC INGESTION TESTS PASSED SUCCESSFULLY!")



