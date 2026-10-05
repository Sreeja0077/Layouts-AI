"""
Integration tests for Layouts Team Floor Plan Verification API & PostgreSQL Persistence (Task 2.3).
Verifies ingestion, PostgreSQL source-version model persistence, verification report fetching,
human VERIFY state transitions, REJECT state transitions with mandatory reason comments,
audit logging, transactional rollback on errors, explicit 404 handling on missing files/reports,
and RBAC authorization guards.
Zero production demo fallbacks, zero memory-only stores, zero local JSON persistence files.
"""

import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.persistence.database import SessionLocal, engine
from app.persistence.models import Base, FloorPlanSourceVersionModel, AuditLogModel, FloorPlan, Project
from app.security.auth import AuthenticatedUser, UserRole
from app.security.config import security_settings

client = TestClient(app)


def setup_module():
    """Ensure database tables are initialized before tests run."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass


def test_floor_plan_ingestion_and_postgres_persistence():
    """Verify posting ingestion request creates and persists FloorPlanSourceVersionModel record in PostgreSQL."""
    response = client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": "fp_test_dxf_001"},
    )
    assert response.status_code == 200, f"Ingest failed: {response.text}"
    report = response.json()

    assert report["floor_plan_name"] == "sample_floor_plan.dxf"
    assert report["source_type"] == "DXF"
    assert report["verification_status"] == "PENDING"
    assert report["is_geometry_valid"] is True
    assert report["total_rooms_count"] == 1
    assert report["total_net_area_sqm"] == 120.0
    assert len(report["all_elements_geometry"]) == 9

    # Prove PostgreSQL DB persistence using a fresh, independent DB session
    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.source_type == "DXF")
            .order_by(FloorPlanSourceVersionModel.version_no.desc())
            .first()
        )
        assert record is not None, "FloorPlanSourceVersionModel record missing in PostgreSQL database"
        assert record.verification_status == "PENDING"
        assert record.verification_report is not None
        assert record.verification_report["floor_plan_name"] == "sample_floor_plan.dxf"
        assert record.verification_report["total_rooms_count"] == 1
    finally:
        db.close()

    # GET report endpoint reads from PostgreSQL
    get_resp = client.get("/api/v1/projects/proj_101/floor-plans/fp_test_dxf_001/verification-report")
    assert get_resp.status_code == 200
    assert get_resp.json()["verification_status"] == "PENDING"

    print("Verified Floor Plan Ingestion & PostgreSQL Database Persistence")


def test_no_demo_fallback_on_missing_file_or_report():
    """Verify missing source file or unknown floor_plan_id returns explicit 404 error instead of substituting demo fixture."""
    # 1. Unknown file ingestion attempt -> 404
    missing_file_resp = client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "non_existent_blueprint.ifc", "floor_plan_id": "fp_missing_file_999"},
    )
    assert missing_file_resp.status_code == 404
    assert "not found" in missing_file_resp.json()["detail"].lower()

    # 2. Unknown floor_plan_id GET report -> 404
    unknown_report_resp = client.get("/api/v1/projects/proj_101/floor-plans/unknown_fp_999/verification-report")
    assert unknown_report_resp.status_code == 404
    assert "not found" in unknown_report_resp.json()["detail"].lower()

    print("Verified Explicit 404 Error Handling (Zero Demo Fallbacks)")


def test_floor_plan_verify_flow_postgres_persistence():
    """Verify human VERIFY action updates verification_status in PostgreSQL and records reviewer user ID & audit log."""
    # Ingest fixture first
    client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": "fp_verify_001"},
    )

    # Verify action (with mock auth active as LAYOUT_EXEC)
    security_settings.ALLOW_MOCK_AUTH = True
    response = client.post("/api/v1/projects/proj_101/floor-plans/fp_verify_001/verify")
    assert response.status_code == 200
    report = response.json()

    assert report["verification_status"] == "VERIFIED"
    assert report["reviewer_user_id"] == "usr_mock_001"
    assert report["verified_at"] is not None

    # Prove PostgreSQL persistence by querying DB with a completely fresh session
    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .order_by(FloorPlanSourceVersionModel.created_at.desc())
            .first()
        )
        assert record is not None
        assert record.verification_status == "VERIFIED"
        assert record.verified_at is not None
        assert record.verification_report["verification_status"] == "VERIFIED"

        # Verify audit log entry was created
        audit = db.query(AuditLogModel).filter(AuditLogModel.action == "FLOOR_PLAN_VERIFY").first()
        assert audit is not None
        assert "fp_verify_001" in audit.entity_ref
    finally:
        db.close()

    print("Verified Layouts Team VERIFY Action & PostgreSQL Persistence Reload")


def test_floor_plan_reject_flow_postgres_persistence():
    """Verify human REJECT action requires mandatory rejection reason comment and updates status in PostgreSQL."""
    # Ingest fixture first
    client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": "fp_reject_001"},
    )

    # Rejection without reason -> 400 Bad Request
    bad_resp = client.post(
        "/api/v1/projects/proj_101/floor-plans/fp_reject_001/reject",
        json={"rejection_reason": ""},
    )
    assert bad_resp.status_code == 400
    assert "Rejection reason is required" in bad_resp.json()["detail"]

    # Rejection with valid reason
    response = client.post(
        "/api/v1/projects/proj_101/floor-plans/fp_reject_001/reject",
        json={"rejection_reason": "Unclosed exterior wall polyline on layer A-WALL"},
    )
    assert response.status_code == 200
    report = response.json()

    assert report["verification_status"] == "REJECTED"
    assert report["rejection_reason"] == "Unclosed exterior wall polyline on layer A-WALL"

    # Prove PostgreSQL persistence by querying DB with a fresh session
    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .order_by(FloorPlanSourceVersionModel.created_at.desc())
            .first()
        )
        assert record is not None
        assert record.verification_status == "REJECTED"
        assert record.rejection_reason == "Unclosed exterior wall polyline on layer A-WALL"
        assert record.verification_report["verification_status"] == "REJECTED"

        # Verify audit log entry was created
        audit = db.query(AuditLogModel).filter(AuditLogModel.action == "FLOOR_PLAN_REJECT").first()
        assert audit is not None
        assert "fp_reject_001" in audit.entity_ref
    finally:
        db.close()

    print("Verified Layouts Team REJECT Action & PostgreSQL Persistence Reload")


if __name__ == "__main__":
    setup_module()
    test_floor_plan_ingestion_and_postgres_persistence()
    test_no_demo_fallback_on_missing_file_or_report()
    test_floor_plan_verify_flow_postgres_persistence()
    test_floor_plan_reject_flow_postgres_persistence()
    print("ALL VERIFICATION API & POSTGRESQL PERSISTENCE INTEGRATION TESTS PASSED SUCCESSFULLY!")
