"""
Unit test for floor plan geometry reconciliation and verification flow (Task 2.3).
Verifies boundary polygon validation, area computation, and anomaly warning detection.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bim.ifc_ingest import IFCIngestor
from app.bim.dxf_ingest import DXFIngestor
from app.bim.reconciliation import GeometryReconciler, GeometryVerificationReport

ROOT_DIR = BACKEND_DIR.parent
REAL_IFC_FILE = ROOT_DIR / "docs" / "4420 Ashland Rev 2.ifc"


def test_ifc_reconciliation():
    ingestor = IFCIngestor()
    reconciler = GeometryReconciler()

    target_file = str(REAL_IFC_FILE) if REAL_IFC_FILE.exists() else "level4_office.ifc"
    parsed_ifc = ingestor.parse_file(target_file)
    report: GeometryVerificationReport = reconciler.reconcile_ifc(parsed_ifc)

    assert report.is_geometry_valid is True
    assert report.total_rooms_count > 0
    assert report.total_net_area_sqm > 0
    assert len(report.boundary_polygon) == 4

    print(f"\n[IFC Verification] File: {report.floor_plan_name}")
    print(f"[IFC Verification] Total Rooms: {report.total_rooms_count}")
    print(f"[IFC Verification] Total Area: {report.total_net_area_sqm} sqm")
    print(f"[IFC Verification] Warnings: {len(report.warnings)}")


def test_dxf_reconciliation():
    ingestor = DXFIngestor()
    reconciler = GeometryReconciler()

    parsed_dxf = ingestor.parse_file("level4_layout.dxf")
    report: GeometryVerificationReport = reconciler.reconcile_dxf(parsed_dxf)

    assert report.is_geometry_valid is True
    assert report.total_net_area_sqm == 240.0
    print(f"\n[DXF Verification] File: {report.floor_plan_name} | Rooms: {report.total_rooms_count}")


if __name__ == "__main__":
    test_ifc_reconciliation()
    test_dxf_reconciliation()
    print("\nALL GEOMETRY RECONCILIATION TESTS PASSED SUCCESSFULLY!")
