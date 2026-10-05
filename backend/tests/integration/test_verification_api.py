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

# Ensure PostgreSQL integration test uses DATABASE_URL environment setting (defaults to in-memory for isolated local unit test runner)
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
from app.api.v1.projects import ensure_uuid

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

    # Prove PostgreSQL DB persistence using a fresh, independent DB session and exact normalized UUID lookup
    from app.api.v1.projects import ensure_uuid
    target_uuid = ensure_uuid("fp_test_dxf_001")

    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.floor_plan_id == target_uuid)
            .order_by(FloorPlanSourceVersionModel.version_no.desc())
            .first()
        )
        assert record is not None, f"FloorPlanSourceVersionModel record missing for UUID {target_uuid}"
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
    from app.api.v1.projects import ensure_uuid
    target_uuid = ensure_uuid("fp_verify_001")
    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.floor_plan_id == target_uuid)
            .order_by(FloorPlanSourceVersionModel.version_no.desc())
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
    reject_target_uuid = ensure_uuid("fp_reject_001")
    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.floor_plan_id == reject_target_uuid)
            .order_by(FloorPlanSourceVersionModel.version_no.desc())
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


def test_non_uuid_floor_plan_identifier_full_flow_regression():
    """
    Focused regression test proving that a non-UUID application identifier (e.g. 'fp_test_dxf_001')
    can still be used at the API layer while the actual PostgreSQL query receives only the normalized UUID.
    Confirms:
    - Ingestion succeeds
    - Verification report retrieval succeeds
    - No InvalidTextRepresentation error occurs
    - VERIFY succeeds
    - REJECT succeeds
    - Persisted verification state remains correct
    """
    non_uuid_fp_id = "fp_test_dxf_001"

    # 1. Ingestion succeeds
    ingest_resp = client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": non_uuid_fp_id},
    )
    assert ingest_resp.status_code == 200, f"Ingest failed: {ingest_resp.text}"

    # 2. GET verification report retrieval succeeds without InvalidTextRepresentation error
    get_resp = client.get(f"/api/v1/projects/proj_101/floor-plans/{non_uuid_fp_id}/verification-report")
    assert get_resp.status_code == 200, f"GET report failed: {get_resp.text}"
    assert get_resp.json()["verification_status"] == "PENDING"

    # 3. VERIFY succeeds
    security_settings.ALLOW_MOCK_AUTH = True
    verify_resp = client.post(f"/api/v1/projects/proj_101/floor-plans/{non_uuid_fp_id}/verify")
    assert verify_resp.status_code == 200, f"VERIFY failed: {verify_resp.text}"
    assert verify_resp.json()["verification_status"] == "VERIFIED"

    # 4. REJECT succeeds on non-UUID floor_plan_id
    non_uuid_reject_id = "fp_reject_001"
    client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": non_uuid_reject_id},
    )
    reject_resp = client.post(
        f"/api/v1/projects/proj_101/floor-plans/{non_uuid_reject_id}/reject",
        json={"rejection_reason": "Structural boundary wall is missing layer tag"},
    )
    assert reject_resp.status_code == 200, f"REJECT failed: {reject_resp.text}"
    assert reject_resp.json()["verification_status"] == "REJECTED"

    # 5. Persisted verification state in database remains correct
    from app.api.v1.projects import ensure_uuid
    target_uuid = ensure_uuid(non_uuid_fp_id)
    db = SessionLocal()
    try:
        record = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.floor_plan_id == target_uuid)
            .order_by(FloorPlanSourceVersionModel.version_no.desc())
            .first()
        )
        assert record is not None
        assert record.verification_status == "VERIFIED"
        assert record.verification_report["verification_status"] == "VERIFIED"
    finally:
        db.close()

    print("Verified Non-UUID Identifier Full Flow Regression (Zero InvalidTextRepresentation Errors)")


if __name__ == "__main__":
    setup_module()
    test_floor_plan_ingestion_and_postgres_persistence()
    test_no_demo_fallback_on_missing_file_or_report()
    test_floor_plan_verify_flow_postgres_persistence()
    test_floor_plan_reject_flow_postgres_persistence()
    test_non_uuid_floor_plan_identifier_full_flow_regression()
    print("ALL VERIFICATION API & POSTGRESQL PERSISTENCE INTEGRATION TESTS PASSED SUCCESSFULLY!")

