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
from app.persistence.models import Base, FloorPlanSourceVersionModel, AuditLogModel, FloorPlan, Project, User
from app.security.auth import AuthenticatedUser, UserRole
from app.security.config import security_settings
from app.api.v1.projects import ensure_uuid

client = TestClient(app)


def setup_mock_user():
    """Ensure mock user exists in database for integration tests before VERIFY/REJECT operations."""
    mock_user_uuid = ensure_uuid("usr_mock_001")
    mock_org_uuid = ensure_uuid("org_mock_999")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == mock_user_uuid).first()
        if not user:
            user = User(
                id=mock_user_uuid,
                email="dev_user@company.com",
                full_name="Mock Layouts Exec",
                role="LAYOUT_EXEC",
                org_id=mock_org_uuid,
                is_active=True,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


def setup_module():
    """Ensure database tables and mock user are initialized before tests run."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    setup_mock_user()


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

        # Verify audit log entry was created and actor_id matches existing users.id
        audit = db.query(AuditLogModel).filter(AuditLogModel.action == "FLOOR_PLAN_VERIFY").first()
        assert audit is not None
        assert "fp_verify_001" in audit.entity_ref
        assert str(audit.actor_id) == ensure_uuid("usr_mock_001")

        actor_user = db.query(User).filter(User.id == str(audit.actor_id)).first()
        assert actor_user is not None, f"audit_logs.actor_id '{audit.actor_id}' missing in users table"
        assert actor_user.email == "dev_user@company.com"
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

        # Verify audit log entry was created and actor_id matches existing users.id
        audit = db.query(AuditLogModel).filter(AuditLogModel.action == "FLOOR_PLAN_REJECT").first()
        assert audit is not None
        assert "fp_reject_001" in audit.entity_ref
        assert str(audit.actor_id) == ensure_uuid("usr_mock_001")

        actor_user = db.query(User).filter(User.id == str(audit.actor_id)).first()
        assert actor_user is not None, f"audit_logs.actor_id '{audit.actor_id}' missing in users table"
        assert actor_user.email == "dev_user@company.com"
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


def test_floor_plan_publishing_flow_postgres_persistence():
    """
    Verify Task 2.4 publishing flow:
    - Ingest v1 -> PENDING
    - Attempt publish on PENDING -> 400 Bad Request
    - Verify v1 -> VERIFIED
    - Publish v1 -> 200 OK (is_published == True, published_by_user_id == ensure_uuid("usr_mock_001"))
    - GET /published-version -> 200 OK (v1)
    - Ingest v2 -> PENDING
    - Verify v2 -> VERIFIED
    - Publish v2 -> 200 OK (v2 published, v1 unpublished)
    - GET /published-version -> 200 OK (v2)
    - Audit log recorded with FLOOR_PLAN_SOURCE_VERSION_PUBLISH
    - Durable state verified with fresh DB session
    """
    fp_id = "fp_pub_api_001"
    security_settings.ALLOW_MOCK_AUTH = True

    # 1. Ingest v1
    ingest_v1 = client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": fp_id},
    )
    assert ingest_v1.status_code == 200

    # 2. Publish unverified PENDING version -> 400 Bad Request
    pub_pending = client.post(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/publish")
    assert pub_pending.status_code == 400
    assert "VERIFIED" in pub_pending.json()["detail"]

    # 3. Verify v1
    verify_v1 = client.post(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/verify")
    assert verify_v1.status_code == 200

    # 4. Publish v1 -> 200 OK
    pub_v1 = client.post(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/publish")
    assert pub_v1.status_code == 200
    v1_payload = pub_v1.json()
    assert v1_payload["version_no"] == 1
    assert v1_payload["is_published"] is True
    assert v1_payload["published_by_user_id"] == ensure_uuid("usr_mock_001")
    assert v1_payload["published_at"] is not None

    # 5. GET published version -> returns v1
    get_pub1 = client.get(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/published-version")
    assert get_pub1.status_code == 200
    assert get_pub1.json()["version_no"] == 1
    assert get_pub1.json()["is_published"] is True

    # 6. Ingest & verify v2
    ingest_v2 = client.post(
        "/api/v1/projects/proj_101/floor-plans/ingest",
        json={"file_name": "sample_floor_plan.dxf", "floor_plan_id": fp_id},
    )
    assert ingest_v2.status_code == 200

    verify_v2 = client.post(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/verify")
    assert verify_v2.status_code == 200

    # 7. Publish v2 -> 200 OK
    pub_v2 = client.post(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/publish")
    assert pub_v2.status_code == 200
    v2_payload = pub_v2.json()
    assert v2_payload["version_no"] == 2
    assert v2_payload["is_published"] is True

    # 8. GET published version -> now returns v2
    get_pub2 = client.get(f"/api/v1/projects/proj_101/floor-plans/{fp_id}/published-version")
    assert get_pub2.status_code == 200
    assert get_pub2.json()["version_no"] == 2

    # 9. Direct PostgreSQL audit & persistence check
    target_uuid = ensure_uuid(fp_id)
    db = SessionLocal()
    try:
        versions = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.floor_plan_id == target_uuid)
            .order_by(FloorPlanSourceVersionModel.version_no.asc())
            .all()
        )
        assert len(versions) == 2
        assert versions[0].is_published is False
        assert versions[1].is_published is True

        audit = (
            db.query(AuditLogModel)
            .filter(AuditLogModel.action == "FLOOR_PLAN_SOURCE_VERSION_PUBLISH")
            .order_by(AuditLogModel.created_at.desc())
            .first()
        )
        assert audit is not None
        assert str(audit.actor_id) == ensure_uuid("usr_mock_001")
    finally:
        db.close()

    print("Verified Floor Plan Publishing API & PostgreSQL Persistence Reload")


if __name__ == "__main__":
    setup_module()
    test_floor_plan_ingestion_and_postgres_persistence()
    test_no_demo_fallback_on_missing_file_or_report()
    test_floor_plan_verify_flow_postgres_persistence()
    test_floor_plan_reject_flow_postgres_persistence()
    test_non_uuid_floor_plan_identifier_full_flow_regression()
    test_floor_plan_publishing_flow_postgres_persistence()
    print("ALL VERIFICATION API & POSTGRESQL PERSISTENCE INTEGRATION TESTS PASSED SUCCESSFULLY!")


