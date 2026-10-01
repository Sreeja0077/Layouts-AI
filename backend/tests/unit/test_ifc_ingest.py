"""
Unit & Integration test for Revit IFC floor plan ingestion engine (Task 2.1).
Verifies real IFC parsing using IfcOpenShell on fixture "docs/4420 Ashland Rev 2.ifc".
Proves actual 2D geometry extraction, GlobalId preservation, unit normalization,
and explicit error handling without mock or placeholder fallbacks.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.ifc_ingest import IFCIngestor, IFCParsedFloorPlan, ExtractedElement

ROOT_DIR = BACKEND_DIR.parent
REAL_IFC_FILE = ROOT_DIR / "docs" / "4420 Ashland Rev 2.ifc"


def test_real_ifc_ingest_parsing():
    """Verify parsing real .ifc file with IfcOpenShell and extracting all 5 mandatory element types."""
    assert REAL_IFC_FILE.exists(), f"Real IFC fixture file missing at {REAL_IFC_FILE}"

    ingestor = IFCIngestor()
    result: IFCParsedFloorPlan = ingestor.parse_file(str(REAL_IFC_FILE))

    print(f"\n[Real IFC Ingestion Test] File: {result.file_name}")
    print(f"[Real IFC Ingestion Test] Total Elements Extracted: {result.total_elements_count}")
    print(f"[Real IFC Ingestion Test] Walls: {len(result.walls)}")
    print(f"[Real IFC Ingestion Test] Doors: {len(result.doors)}")
    print(f"[Real IFC Ingestion Test] Windows: {len(result.windows)}")
    print(f"[Real IFC Ingestion Test] Columns: {len(result.columns)}")
    print(f"[Real IFC Ingestion Test] Spaces: {len(result.spaces)}")
    print(f"[Real IFC Ingestion Test] Declared Unit: {result.source_metadata.get('declared_length_unit')}")
    print(f"[Real IFC Ingestion Test] Scale Factor to Meters: {result.source_metadata.get('unit_scale_to_meters')}")

    # 1. Total elements > 0
    assert result.total_elements_count > 0, "No elements extracted from real IFC file!"

    # 2. Verify all 5 mandatory element types exist in real file fixture
    assert len(result.walls) > 0, "Expected IfcWall elements in 4420 Ashland Rev 2.ifc"
    assert len(result.doors) > 0, "Expected IfcDoor elements in 4420 Ashland Rev 2.ifc"
    assert len(result.windows) > 0, "Expected IfcWindow elements in 4420 Ashland Rev 2.ifc"
    assert len(result.columns) > 0, "Expected IfcColumn elements in 4420 Ashland Rev 2.ifc"
    assert len(result.spaces) > 0, "Expected IfcSpace elements in 4420 Ashland Rev 2.ifc"

    # 3. Verify GlobalIds, boundaries, properties, and metadata for every element
    all_elements = result.walls + result.doors + result.windows + result.columns + result.spaces
    for elem in all_elements:
        # GlobalId preservation
        assert elem.ifc_global_id and len(elem.ifc_global_id) > 0, f"Element {elem.internal_id} missing ifc_global_id!"
        assert elem.global_id == elem.ifc_global_id, "global_id and ifc_global_id mismatch!"
        assert elem.element_type and elem.element_type.startswith("Ifc"), f"Invalid element_type {elem.element_type}"

        # 2D Boundary verification
        assert len(elem.boundary_vertices) >= 3, (
            f"Element {elem.ifc_global_id} must have at least 3 vertices for a 2D footprint polygon!"
        )
        for vertex in elem.boundary_vertices:
            assert len(vertex) == 2, f"Vertex {vertex} must be a 2D [x, y] coordinate!"
            assert isinstance(vertex[0], (int, float)) and isinstance(vertex[1], (int, float))

    # 4. Source metadata verification
    assert result.source_metadata.get("declared_length_unit") in ["FOOT", "METRE"], "Declared unit missing or unrecognized!"
    assert result.source_metadata.get("unit_scale_to_meters") is not None
    assert result.file_name == REAL_IFC_FILE.name

    print("REAL IFC FILE PARSING VERIFIED SUCCESSFULLY!")


def test_geometry_variation_and_no_placeholder_coordinates():
    """Regression test proving that real extracted geometry varies between elements and is not static placeholder."""
    ingestor = IFCIngestor()
    result = ingestor.parse_file(str(REAL_IFC_FILE))

    # Static placeholder coordinates from old implementation
    old_placeholder_1 = [[0.0, 0.0], [5.0, 0.0], [5.0, 0.2], [0.0, 0.2]]
    old_placeholder_2 = [[0.0, 0.0], [4.0, 0.0], [4.0, 0.2], [0.0, 0.2]]

    # Compare geometry across wall elements
    wall_footprints = [w.boundary_vertices for w in result.walls]
    for fp in wall_footprints:
        assert fp != old_placeholder_1, "Parser returned static placeholder geometry [[0.0, 0.0], [5.0, 0.0], [5.0, 0.2], [0.0, 0.2]]!"
        assert fp != old_placeholder_2, "Parser returned static placeholder geometry [[0.0, 0.0], [4.0, 0.0], [4.0, 0.2], [0.0, 0.2]]!"

    # Verify distinct geometric variation across walls
    unique_footprints = {tuple(tuple(v) for v in fp) for fp in wall_footprints}
    assert len(unique_footprints) > 1, f"Expected distinct geometry across walls, found only {len(unique_footprints)} unique footprint!"

    print(f"VERIFIED GEOMETRY VARIATION: {len(unique_footprints)} unique footprints found across {len(result.walls)} walls.")


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
    test_geometry_variation_and_no_placeholder_coordinates()
    test_missing_file_raises_explicit_error()
    test_malformed_file_raises_explicit_error()
    print("\nALL REVIT IFC INGESTION TESTS PASSED SUCCESSFULLY!")
