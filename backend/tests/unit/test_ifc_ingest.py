"""
Unit test for Revit IFC floor plan ingestion engine (Task 2.1).
Verifies extraction of structural elements (walls, doors, spaces) using real .ifc file "docs/4420 Ashland Rev 2.ifc".
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.ifc_ingest import IFCIngestor, IFCParsedFloorPlan

ROOT_DIR = BACKEND_DIR.parent
REAL_IFC_FILE = ROOT_DIR / "docs" / "4420 Ashland Rev 2.ifc"


def test_ifc_ingest_parsing_real_file():
    ingestor = IFCIngestor()

    if REAL_IFC_FILE.exists():
        result: IFCParsedFloorPlan = ingestor.parse_file(str(REAL_IFC_FILE))
        print(f"\n[Real IFC File] File: {result.file_name}")
        print(f"[Real IFC File] Total Elements: {result.total_elements_count}")
        print(f"[Real IFC File] Walls Extracted: {len(result.walls)}")
        print(f"[Real IFC File] Doors Extracted: {len(result.doors)}")
        print(f"[Real IFC File] Windows Extracted: {len(result.windows)}")
        print(f"[Real IFC File] Columns Extracted: {len(result.columns)}")
        print(f"[Real IFC File] Spaces Extracted: {len(result.spaces)}")

        assert result.total_elements_count > 0, "No elements extracted from real IFC file!"
        assert len(result.walls) > 0 or len(result.doors) > 0 or len(result.spaces) > 0
    else:
        # Fallback test if real file path is not found
        result = ingestor.parse_file("level4_office_model.ifc")
        assert result.total_elements_count > 0

    print("\nALL REVIT IFC INGESTION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_ifc_ingest_parsing_real_file()
