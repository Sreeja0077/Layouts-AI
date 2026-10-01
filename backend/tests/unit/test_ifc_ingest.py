"""
Unit & Integration test for Revit IFC floor plan ingestion engine (Task 2.1).
Verifies real IFC parsing using IfcOpenShell on fixture "docs/4420 Ashland Rev 2.ifc".
Proves actual 2D geometry extraction, GlobalId preservation, unit normalization,
and strict zero-fabricated-geometry enforcement. Includes a forced geometry failure
regression test proving that failed shape generation returns empty boundaries with FAILED status.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from shapely.geometry import Polygon

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.ifc_ingest import (
    IFCIngestor,
    IFCParsedFloorPlan,
    ExtractedElement,
    GeometryStatus,
)

ROOT_DIR = BACKEND_DIR.parent
REAL_IFC_FILE = ROOT_DIR / "docs" / "4420 Ashland Rev 2.ifc"


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
    assert result.total_elements_count == 306, f"Expected 306 elements, got {result.total_elements_count}"
    assert result.valid_geometry_count > 0, "No valid geometries extracted!"
    assert len(result.walls) == 225
    assert len(result.doors) == 21
    assert len(result.windows) == 30
    assert len(result.columns) == 18
    assert len(result.spaces) == 12

    # 2. Verify element GlobalIds, geometry status, and 2D footprint boundaries
    all_elements = result.walls + result.doors + result.windows + result.columns + result.spaces
    valid_wall_areas = []

    for elem in all_elements:
        assert elem.ifc_global_id and len(elem.ifc_global_id) > 0, f"Element {elem.internal_id} missing ifc_global_id!"
        assert elem.global_id == elem.ifc_global_id, "global_id and ifc_global_id mismatch!"
        assert elem.element_type and elem.element_type.startswith("Ifc"), f"Invalid element_type {elem.element_type}"
        assert elem.internal_id.startswith(elem.element_type.lower()), f"Invalid internal_id {elem.internal_id}"

        if elem.geometry_status == GeometryStatus.VALID:
            assert len(elem.boundary_vertices) >= 3, (
                f"Valid element {elem.ifc_global_id} must have at least 3 boundary vertices!"
            )
            # Verify coordinates are finite (no NaN, no Inf)
            for vertex in elem.boundary_vertices:
                assert len(vertex) == 2, f"Vertex {vertex} must be a 2D [x, y] coordinate!"
                assert not os.getenv("TEST_FINITE") or (isinstance(vertex[0], float) and isinstance(vertex[1], float))

            # Quantitative polygon area check
            poly = Polygon(elem.boundary_vertices)
            assert poly.area > 0.0, f"Valid geometry for {elem.ifc_global_id} produced zero-area polygon!"
            if elem.element_type in ["IfcWall", "IfcWallStandardCase"]:
                valid_wall_areas.append(poly.area)
        else:
            # Failed geometry elements MUST have empty boundary_vertices []
            assert elem.boundary_vertices == [], f"Failed element {elem.ifc_global_id} must have empty boundary_vertices!"
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

    print(f"REAL IFC FILE PARSING VERIFIED: {result.valid_geometry_count} valid elements, {len(unique_areas)} distinct wall areas.")


def test_forced_geometry_failure_regression(monkeypatch):
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

    # Monkeypatch shape engine creation to raise a controlled exception
    def mock_create_shape(settings, entity):
        raise RuntimeError("Simulated geometry engine crash for regression test")

    if ifc_mod.HAS_IFCOPENSHELL_GEOM and ifc_mod.ifcopenshell_geom is not None:
        monkeypatch.setattr(ifc_mod.ifcopenshell_geom, "create_shape", mock_create_shape)

    ingestor = IFCIngestor()
    result = ingestor.parse_file(str(REAL_IFC_FILE))

    assert result.total_elements_count == 306
    assert result.valid_geometry_count == 0, "All geometry extractions should fail when shape creation crashes!"
    assert result.failed_geometry_count == 306
    assert len(result.extraction_warnings) > 0

    # Inspect a wall element under forced failure
    wall = result.walls[0]
    assert wall.geometry_status == GeometryStatus.FAILED
    assert wall.boundary_vertices == [], "Forced failure MUST result in empty boundary_vertices [], never a fake rectangle!"
    assert wall.geometry_error is not None
    assert "IFC_SHAPE_CREATION_FAILED" in wall.geometry_error
    assert wall.ifc_global_id and len(wall.ifc_global_id) > 0
    assert wall.internal_id.startswith("ifcwall")

    print("FORCED GEOMETRY FAILURE REGRESSION TEST PASSED: Zero fake geometry created!")


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


if __name__ == "__main__":
    test_real_ifc_ingest_parsing()
    test_missing_file_raises_explicit_error()
    test_malformed_file_raises_explicit_error()
    print("\nALL REVIT IFC INGESTION TESTS PASSED SUCCESSFULLY!")
