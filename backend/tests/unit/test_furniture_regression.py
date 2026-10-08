"""
Furniture Regression Tests — Layouts AI.

Validates that the authoritative IFC ingestion / reconciliation pipeline correctly
extracts, counts, and persists furniture elements. These tests operate on the actual
parsed-IFC model and reconciled verification report — not on frontend stubs.

Test matrix:
- Furniture items survive IFC ingestion through to the GeometryVerificationReport.
- elements_summary["furniture_items"] correctly reflects the parsed count.
- all_elements_geometry contains FURNITURE_ITEM category entries.
- _is_report_structurally_incomplete correctly identifies stale reports.
- Legacy-report refresh restores furniture from the source IFC (persisted-report path).
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict

from app.bim.ifc_ingest import (
    IFCParsedFloorPlan,
    ExtractedElement,
    GeometryStatus,
    GeometryType,
)
from app.bim.reconciliation import (
    GeometryReconciler,
    GeometryVerificationReport,
    VerificationStatus,
)
from app.api.v1.projects import _is_report_structurally_incomplete


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_element(
    internal_id: str,
    element_type: str,
    category: str,
    name: str = "Item",
    storey_name: str = "Level 1",
) -> ExtractedElement:
    elem = ExtractedElement(
        internal_id=internal_id,
        ifc_global_id=internal_id,
        global_id=internal_id,
        element_type=element_type,
        category=category,
        name=name,
        geometry_status=GeometryStatus.VALID,
        geometry_type=GeometryType.POLYGON,
        geometry_coordinates=[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
        boundary_vertices=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        properties={"storey_name": storey_name, "storey_elevation_m": 0.0},
    )
    return elem


def _make_parsed_ifc(
    wall_count: int = 4,
    door_count: int = 1,
    window_count: int = 1,
    space_count: int = 1,
    furniture_count: int = 5,
) -> IFCParsedFloorPlan:
    walls = [_make_element(f"w{i}", "IfcWall", "WALL", f"Wall {i}") for i in range(wall_count)]
    doors = [_make_element(f"d{i}", "IfcDoor", "DOOR", f"Door {i}") for i in range(door_count)]
    windows = [_make_element(f"win{i}", "IfcWindow", "WINDOW", f"Win {i}") for i in range(window_count)]
    spaces = [_make_element(f"sp{i}", "IfcSpace", "SPACE", f"Room {i}") for i in range(space_count)]
    furniture = [
        _make_element(f"furn{i}", "IfcFurnishingElement", "FURNITURE_ITEM", f"Desk {i}")
        for i in range(furniture_count)
    ]
    total = wall_count + door_count + window_count + space_count + furniture_count
    return IFCParsedFloorPlan(
        file_name="test.ifc",
        total_elements_count=total,
        walls=walls,
        doors=doors,
        windows=windows,
        columns=[],
        spaces=spaces,
        furniture=furniture,
        source_metadata={"file_name": "test.ifc"},
    )


# ---------------------------------------------------------------------------
# Test: furniture survives reconcile_ifc
# ---------------------------------------------------------------------------

class TestFurnitureSurvivesReconciliation:
    def test_furniture_items_in_elements_summary(self):
        parsed = _make_parsed_ifc(furniture_count=7)
        report = GeometryReconciler().reconcile_ifc(parsed)
        assert "furniture_items" in report.elements_summary
        assert report.elements_summary["furniture_items"] == 7

    def test_furniture_category_in_all_elements_geometry(self):
        parsed = _make_parsed_ifc(furniture_count=3)
        report = GeometryReconciler().reconcile_ifc(parsed)
        furniture_entries = [
            e for e in report.all_elements_geometry
            if "FURNITURE" in str(e.get("category", "")).upper()
        ]
        assert len(furniture_entries) == 3

    def test_zero_furniture_produces_zero_count(self):
        parsed = _make_parsed_ifc(furniture_count=0)
        report = GeometryReconciler().reconcile_ifc(parsed)
        assert report.elements_summary.get("furniture_items", -1) == 0

    def test_furniture_storey_preserved(self):
        parsed = _make_parsed_ifc(furniture_count=2)
        report = GeometryReconciler().reconcile_ifc(parsed)
        furniture_entries = [
            e for e in report.all_elements_geometry
            if "FURNITURE" in str(e.get("category", "")).upper()
        ]
        for entry in furniture_entries:
            storey = entry.get("storey_name") or (entry.get("properties") or {}).get("storey_name")
            assert storey == "Level 1", f"Bad storey: {storey!r} for {entry.get('id')}"


# ---------------------------------------------------------------------------
# Test: _is_report_structurally_incomplete
# ---------------------------------------------------------------------------

class TestIsReportStructurallyIncomplete:
    def _complete_report(self) -> Dict[str, Any]:
        return {
            "available_storeys": [{"name": "Level 1"}],
            "is_geometry_valid": True,
            "all_elements_geometry": [
                {"id": "w1", "category": "WALL", "storey_name": "Level 1"},
                {"id": "furn1", "category": "FURNITURE_ITEM", "storey_name": "Level 1"},
            ],
            "elements_summary": {"furniture_items": 1, "walls": 1},
        }

    def test_complete_report_not_flagged(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        assert not _is_report_structurally_incomplete(self._complete_report(), src)

    def test_missing_available_storeys_triggers_refresh(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        r = self._complete_report(); r["available_storeys"] = []
        assert _is_report_structurally_incomplete(r, src)

    def test_no_storey_name_on_elements_triggers_refresh(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        r = {"available_storeys": [], "is_geometry_valid": True,
             "all_elements_geometry": [{"id": "w1", "category": "WALL"}],
             "elements_summary": {"furniture_items": 0}}
        assert _is_report_structurally_incomplete(r, src)

    def test_furniture_in_geom_but_zero_in_summary_triggers(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        r = self._complete_report(); r["elements_summary"]["furniture_items"] = 0
        assert _is_report_structurally_incomplete(r, src)

    def test_furniture_in_geom_missing_from_summary_triggers(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        r = self._complete_report(); del r["elements_summary"]["furniture_items"]
        assert _is_report_structurally_incomplete(r, src)

    def test_invalid_empty_report_not_flagged_if_not_valid(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        r = {"available_storeys": [{"name": "Level 1"}], "is_geometry_valid": False,
             "all_elements_geometry": [], "elements_summary": {"furniture_items": 0}}
        assert not _is_report_structurally_incomplete(r, src)

    def test_valid_flag_with_empty_geom_triggers(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        r = {"available_storeys": [{"name": "Level 1"}], "is_geometry_valid": True,
             "all_elements_geometry": [], "elements_summary": {"furniture_items": 0}}
        assert _is_report_structurally_incomplete(r, src)

    def test_empty_dict_triggers(self, tmp_path):
        src = tmp_path / "m.ifc"; src.touch()
        assert _is_report_structurally_incomplete({}, src)


# ---------------------------------------------------------------------------
# Test: legacy report refresh restores furniture (persisted-report path)
# ---------------------------------------------------------------------------

class TestLegacyReportRefresh:
    def _stale_record(self, tmp_path, report: Dict, source_type: str = "IFC") -> MagicMock:
        ifc_path = tmp_path / "test.ifc"
        ifc_path.write_bytes(b"ISO-10303-21;\n")
        rec = MagicMock()
        rec.source_type = source_type
        rec.file_storage_path = str(ifc_path)
        rec.verification_report = report
        rec.ifc_export_metadata = {}
        return rec

    def test_stale_report_furniture_restored(self, tmp_path):
        from app.api.v1.projects import _refresh_legacy_ifc_report
        stale = {"available_storeys": [], "is_geometry_valid": True,
                 "all_elements_geometry": [], "elements_summary": {"furniture_items": 0},
                 "verification_status": "PENDING", "reviewer_user_id": None,
                 "verified_at": None, "rejection_reason": None}
        record = self._stale_record(tmp_path, stale)
        db = MagicMock()
        refreshed = GeometryReconciler().reconcile_ifc(_make_parsed_ifc(furniture_count=5))
        with patch("app.api.v1.projects.IFCIngestor") as MI, \
             patch("app.api.v1.projects.reconciler") as MR:
            MI.return_value.parse_file.return_value = _make_parsed_ifc(furniture_count=5)
            MR.reconcile_ifc.return_value = refreshed
            result = _refresh_legacy_ifc_report(record, db)
        furn_count = sum(
            1 for e in result.get("all_elements_geometry", [])
            if "FURNITURE" in str(e.get("category", "")).upper()
        )
        assert furn_count == 5

    def test_workflow_state_preserved(self, tmp_path):
        from app.api.v1.projects import _refresh_legacy_ifc_report
        stale = {"available_storeys": [], "is_geometry_valid": True,
                 "all_elements_geometry": [], "elements_summary": {"furniture_items": 0},
                 "verification_status": "VERIFIED", "reviewer_user_id": "user_abc",
                 "verified_at": "2026-10-01T12:00:00", "rejection_reason": None}
        record = self._stale_record(tmp_path, stale)
        db = MagicMock()
        refreshed = GeometryReconciler().reconcile_ifc(_make_parsed_ifc(furniture_count=3))
        with patch("app.api.v1.projects.IFCIngestor") as MI, \
             patch("app.api.v1.projects.reconciler") as MR:
            MI.return_value.parse_file.return_value = _make_parsed_ifc(furniture_count=3)
            MR.reconcile_ifc.return_value = refreshed
            result = _refresh_legacy_ifc_report(record, db)
        assert result.get("verification_status") == "VERIFIED"
        assert result.get("reviewer_user_id") == "user_abc"
        assert result.get("verified_at") == "2026-10-01T12:00:00"

    def test_dxf_source_not_refreshed(self, tmp_path):
        from app.api.v1.projects import _refresh_legacy_ifc_report
        stale = {"available_storeys": [], "is_geometry_valid": True, "all_elements_geometry": []}
        record = self._stale_record(tmp_path, stale, source_type="DXF")
        db = MagicMock()
        with patch("app.api.v1.projects.IFCIngestor") as MI:
            result = _refresh_legacy_ifc_report(record, db)
            MI.assert_not_called()
        assert result == stale

    def test_complete_report_not_re_ingested(self, tmp_path):
        from app.api.v1.projects import _refresh_legacy_ifc_report
        complete = {
            "available_storeys": [{"name": "Level 1"}],
            "is_geometry_valid": True,
            "all_elements_geometry": [
                {"id": "w1", "category": "WALL", "storey_name": "Level 1"},
                {"id": "f1", "category": "FURNITURE_ITEM", "storey_name": "Level 1"},
            ],
            "elements_summary": {"furniture_items": 1},
            "verification_status": "READY",
            "reviewer_user_id": None, "verified_at": None, "rejection_reason": None,
        }
        record = self._stale_record(tmp_path, complete)
        db = MagicMock()
        with patch("app.api.v1.projects.IFCIngestor") as MI:
            result = _refresh_legacy_ifc_report(record, db)
            MI.assert_not_called()
        assert result["elements_summary"]["furniture_items"] == 1
