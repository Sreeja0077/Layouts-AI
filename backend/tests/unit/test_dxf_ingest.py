"""
Unit test for 2D AutoCAD DXF floor plan ingestion engine (Task 2.2).
Verifies extraction of classified CAD entities (walls, doors, spaces) and polyline boundaries.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.dxf_ingest import DXFIngestor, DXFParsedFloorPlan


def test_dxf_ingest_parsing():
    ingestor = DXFIngestor()
    result: DXFParsedFloorPlan = ingestor.parse_file("level4_layout.dxf")

    assert result.total_entities_count > 0
    assert len(result.layers_found) > 0
    assert len(result.extracted_entities) > 0

    # Verify entity classification
    wall = result.extracted_entities[0]
    assert wall.category == "WALL"
    assert wall.is_closed is True
    assert len(wall.coordinates) == 4

    print("ALL 2D DXF CAD INGESTION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_dxf_ingest_parsing()
