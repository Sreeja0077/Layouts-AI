"""
Unit & Integration test for 2D AutoCAD DXF floor plan ingestion engine (Task 2.2).
Verifies real DXF parsing using ezdxf on fixture "docs/fixtures/sample_floor_plan.dxf".
Proves actual CAD entity extraction (LWPOLYLINE, LINE, ARC, CIRCLE), layer classification,
coordinate accuracy, Pydantic JSON serialization, and strict zero-fabricated-geometry enforcement.
"""

import json
import os
import tempfile
import sys
import pytest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.dxf_ingest import (
    DXFIngestor,
    DXFParsedFloorPlan,
    DXFEntity,
)

ROOT_DIR = BACKEND_DIR.parent
REAL_DXF_FILE = ROOT_DIR / "docs" / "fixtures" / "sample_floor_plan.dxf"


def test_real_dxf_file_parsing():
    """Verify parsing a real DXF fixture with ezdxf and extracting all classified categories."""
    assert REAL_DXF_FILE.exists(), f"Real DXF fixture file missing at {REAL_DXF_FILE}"

    ingestor = DXFIngestor()
    result: DXFParsedFloorPlan = ingestor.parse_file(str(REAL_DXF_FILE))

    print(f"\n[Real DXF Ingestion Test] File: {result.file_name}")
    print(f"[Real DXF Ingestion Test] Total Extracted Entities: {result.total_entities_count}")
    print(f"[Real DXF Ingestion Test] Layers Found: {result.layers_found}")
    print(f"[Real DXF Ingestion Test] Categories Count: {result.entities_by_category}")

    # 1. Total entities & layers
    assert result.total_entities_count == 9, f"Expected 9 extracted entities, got {result.total_entities_count}"
    assert len(result.extracted_entities) == 9
    assert sum(result.entities_by_category.values()) == 9
    assert sorted(result.layers_found) == ["A-COLUMN", "A-DOOR", "A-FURN", "A-ROOM", "A-WALL", "A-WINDOW"]

    # 2. Category classification verification
    cats = result.entities_by_category
    assert cats.get("WALL") == 2, f"Expected 2 WALL entities, got {cats.get('WALL')}"
    assert cats.get("DOOR") == 2, f"Expected 2 DOOR entities, got {cats.get('DOOR')}"
    assert cats.get("WINDOW") == 1, f"Expected 1 WINDOW entity, got {cats.get('WINDOW')}"
    assert cats.get("COLUMN") == 2, f"Expected 2 COLUMN entities, got {cats.get('COLUMN')}"
    assert cats.get("SPACE") == 1, f"Expected 1 SPACE entity, got {cats.get('SPACE')}"
    assert cats.get("FURNITURE") == 1, f"Expected 1 FURNITURE entity, got {cats.get('FURNITURE')}"

    # 3. Entity geometry & coordinate verification
    wall_poly = next(e for e in result.extracted_entities if e.layer_name == "A-WALL" and e.entity_type in ("LWPOLYLINE", "POLYLINE"))
    assert wall_poly.category == "WALL"
    assert wall_poly.is_closed is True
    assert wall_poly.coordinates == [[0.0, 0.0], [20.0, 0.0], [20.0, 12.0], [0.0, 12.0]]

    interior_wall = next(e for e in result.extracted_entities if e.layer_name == "A-WALL" and e.entity_type == "LINE")
    assert interior_wall.category == "WALL"
    assert interior_wall.is_closed is False
    assert interior_wall.coordinates == [[10.0, 0.0], [10.0, 8.0]]

    door_arc = next(e for e in result.extracted_entities if e.layer_name == "A-DOOR" and e.entity_type == "ARC")
    assert door_arc.category == "DOOR"
    assert door_arc.is_closed is False
    assert len(door_arc.coordinates) >= 5

    circle_col = next(e for e in result.extracted_entities if e.layer_name == "A-COLUMN" and e.entity_type == "CIRCLE")
    assert circle_col.category == "COLUMN"
    assert circle_col.is_closed is True
    assert len(circle_col.coordinates) == 17  # 16 segments + closing point

    # 4. Focused POLYLINE regression assertions
    polyline_entities = [e for e in result.extracted_entities if e.entity_type == "POLYLINE"]
    assert len(polyline_entities) == 4, f"Expected 4 POLYLINE entities, got {len(polyline_entities)}"

    poly_wall = next(e for e in polyline_entities if e.layer_name == "A-WALL")
    assert poly_wall.category == "WALL"
    assert poly_wall.is_closed is True
    assert poly_wall.coordinates == [[0.0, 0.0], [20.0, 0.0], [20.0, 12.0], [0.0, 12.0]]

    poly_col = next(e for e in polyline_entities if e.layer_name == "A-COLUMN")
    assert poly_col.category == "COLUMN"
    assert poly_col.is_closed is True
    assert poly_col.coordinates == [[4.0, 4.0], [6.0, 4.0], [6.0, 6.0], [4.0, 6.0]]

    poly_space = next(e for e in polyline_entities if e.layer_name == "A-ROOM")
    assert poly_space.category == "SPACE"
    assert poly_space.is_closed is True
    assert poly_space.coordinates == [[0.0, 0.0], [10.0, 0.0], [10.0, 12.0], [0.0, 12.0]]

    poly_furn = next(e for e in polyline_entities if e.layer_name == "A-FURN")
    assert poly_furn.category == "FURNITURE"
    assert poly_furn.is_closed is True
    assert poly_furn.coordinates == [[2.0, 2.0], [4.0, 2.0], [4.0, 3.0], [2.0, 3.0]]

    print("REAL DXF FILE PARSING VERIFIED: 9 extracted entities across 6 layers (including 4 POLYLINE boundaries).")


def test_dxf_pydantic_serialization():
    """Verify clean Pydantic JSON serialization for parsed DXF floor plans."""
    ingestor = DXFIngestor()
    result = ingestor.parse_file(str(REAL_DXF_FILE))

    dump_dict = result.model_dump()
    assert dump_dict["total_entities_count"] == 9
    assert dump_dict["file_name"] == REAL_DXF_FILE.name

    json_str = result.model_dump_json()
    assert isinstance(json_str, str) and len(json_str) > 500

    parsed_back = json.loads(json_str)
    assert parsed_back["file_name"] == REAL_DXF_FILE.name
    assert len(parsed_back["extracted_entities"]) == 9
    assert parsed_back["entities_by_category"]["WALL"] == 2

    print("DXF PYDANTIC JSON SERIALIZATION TEST PASSED: Clean serialization verified!")


def test_missing_dxf_file_raises_file_not_found():
    """Verify missing DXF path raises explicit FileNotFoundError without mock fallback."""
    ingestor = DXFIngestor()
    with pytest.raises(FileNotFoundError) as exc_info:
        ingestor.parse_file("non_existent_dxf_file_12345.dxf")
    assert "DXF file not found" in str(exc_info.value)
    print("VERIFIED EXPLICIT FileNotFoundError FOR MISSING DXF FILE!")


def test_malformed_dxf_file_raises_value_error():
    """Verify malformed DXF content raises explicit ValueError."""
    ingestor = DXFIngestor()
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False, mode="w") as tmp:
        tmp.write("INVALID_DXF_HEADER_CONTENT_99999\n0\nNOT_A_VALID_DXF")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError) as exc_info:
            ingestor.parse_file(tmp_path)
        assert "Failed to open or parse DXF file" in str(exc_info.value)
        print("VERIFIED EXPLICIT ValueError FOR MALFORMED DXF FILE!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_empty_dxf_file_returns_zero_entities():
    """Verify valid DXF file with empty modelspace returns zero extracted entities cleanly."""
    ingestor = DXFIngestor()
    empty_dxf_content = """0
SECTION
2
ENTITIES
0
ENDSEC
0
EOF"""
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False, mode="w") as tmp:
        tmp.write(empty_dxf_content)
        tmp_path = tmp.name

    try:
        result = ingestor.parse_file(tmp_path)
        assert result.total_entities_count == 0
        assert len(result.extracted_entities) == 0
        assert result.entities_by_category == {}
        print("VERIFIED EMPTY DXF FILE HANDLING: 0 entities extracted.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    test_real_dxf_file_parsing()
    test_dxf_pydantic_serialization()
    test_missing_dxf_file_raises_file_not_found()
    test_malformed_dxf_file_raises_value_error()
    test_empty_dxf_file_returns_zero_entities()
    print("\nALL 2D DXF CAD INGESTION TESTS PASSED SUCCESSFULLY!")
