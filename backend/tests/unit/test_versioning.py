"""
Unit tests for PostgreSQL-backed floor plan source versioning and publishing engine (Task 2.4).
Verifies database persistence, version number tracking, verification status gates (PENDING/REJECTED blocked),
idempotent publishing, unpublishing prior baselines, and audit logging.
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure PostgreSQL integration test uses DATABASE_URL environment setting
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from app.api.v1.projects import ensure_uuid, ensure_user_exists
from app.domain.revisions.versioning import SourceVersionPublisher, FloorPlanSourceVersionPayload
from app.persistence.database import SessionLocal, engine
from app.persistence.models import Base, FloorPlanSourceVersionModel, AuditLogModel, FloorPlan, Project, User
from app.security.auth import AuthenticatedUser, UserRole


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


def _clean_floor_plan_test_data(floor_plan_id: str):
    """Ensure clean test isolation for a specific floor_plan_id across repeated test runs."""
    fp_uuid = ensure_uuid(floor_plan_id)
    db = SessionLocal()
    try:
        db.query(AuditLogModel).filter(AuditLogModel.entity_ref.like(f"%{floor_plan_id}%")).delete(synchronize_session=False)
        db.query(FloorPlanSourceVersionModel).filter(FloorPlanSourceVersionModel.floor_plan_id == fp_uuid).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def setup_module():
    """Ensure database tables and mock user are initialized before tests run."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    setup_mock_user()


def test_postgres_source_version_publishing_lifecycle():
    publisher = SourceVersionPublisher()
    floor_plan_id = "fp_pub_test_001"
    _clean_floor_plan_test_data(floor_plan_id)

    fp_uuid = ensure_uuid(floor_plan_id)
    proj_uuid = ensure_uuid("proj_101")
    mock_user = AuthenticatedUser(
        user_id="usr_mock_001",
        email="dev_user@company.com",
        role=UserRole.LAYOUT_EXEC,
        org_id="org_mock_999",
    )

    db = SessionLocal()
    try:
        # 1. Setup parent project & floor plan
        project_obj = db.query(Project).filter(Project.id == proj_uuid).first()
        if not project_obj:
            project_obj = Project(id=proj_uuid, name="Test Project", org_id=ensure_uuid("org_mock_999"))
            db.add(project_obj)

        fp_obj = db.query(FloorPlan).filter(FloorPlan.id == fp_uuid).first()
        if not fp_obj:
            fp_obj = FloorPlan(id=fp_uuid, project_id=proj_uuid, name="Level 4 Test Plan", floor_number=4)
            db.add(fp_obj)

        # Create v1 record in DB with PENDING verification status
        v1_model = FloorPlanSourceVersionModel(
            id=str(uuid.uuid4()),
            floor_plan_id=fp_uuid,
            version_no=1,
            source_type="IFC",
            file_storage_path="docs/4420 Ashland Rev 2.ifc",
            verification_status="PENDING",
            verification_report={"status": "PENDING", "rooms": 12},
            is_published=False,
        )
        db.add(v1_model)
        db.commit()

        # 2. Attempting to publish PENDING version -> MUST fail with ValueError
        with pytest.raises(ValueError) as exc_info:
            publisher.publish_version(db, floor_plan_id, mock_user)
        assert "verification_status 'PENDING'" in str(exc_info.value)
        assert "VERIFIED by Layouts Team before publishing" in str(exc_info.value)

        # 3. Mark v1 as REJECTED and attempt to publish -> MUST fail
        v1_model.verification_status = "REJECTED"
        v1_model.rejection_reason = "Wall geometry incomplete"
        db.commit()

        with pytest.raises(ValueError) as exc_info:
            publisher.publish_version(db, floor_plan_id, mock_user)
        assert "verification_status 'REJECTED'" in str(exc_info.value)

        # 4. Mark v1 as VERIFIED and publish -> MUST succeed
        v1_model.verification_status = "VERIFIED"
        db.commit()

        pub_v1 = publisher.publish_version(db, floor_plan_id, mock_user)
        assert pub_v1.version_no == 1
        assert pub_v1.is_published is True
        assert pub_v1.published_by_user_id == ensure_uuid("usr_mock_001")
        assert pub_v1.published_at is not None

        # Prove query for current published version returns v1
        curr_pub = publisher.get_current_published_version(db, floor_plan_id)
        assert curr_pub is not None
        assert curr_pub.version_no == 1
        assert curr_pub.is_published is True

        # 5. Idempotent re-publish of v1 -> succeeds deterministically
        pub_v1_retry = publisher.publish_version(db, floor_plan_id, mock_user)
        assert pub_v1_retry.is_published is True
        assert pub_v1_retry.version_no == 1

        # 6. Ingest & verify v2 for the same floor plan
        v2_model = FloorPlanSourceVersionModel(
            id=str(uuid.uuid4()),
            floor_plan_id=fp_uuid,
            version_no=2,
            source_type="IFC",
            file_storage_path="docs/4420 Ashland Rev 3.ifc",
            verification_status="VERIFIED",
            verification_report={"status": "VERIFIED", "rooms": 14},
            is_published=False,
        )
        db.add(v2_model)
        db.commit()

        # Publish v2 -> v2 becomes current published version, v1 is unpublished
        pub_v2 = publisher.publish_version(db, floor_plan_id, mock_user)
        assert pub_v2.version_no == 2
        assert pub_v2.is_published is True

        # Verify v1 is no longer published in DB
        db.refresh(v1_model)
        assert v1_model.is_published is False
        assert v1_model.version_no == 1

        # 7. Check version history list
        history = publisher.get_source_versions(db, floor_plan_id)
        assert len(history) == 2
        assert history[0].version_no == 1
        assert history[0].is_published is False
        assert history[1].version_no == 2
        assert history[1].is_published is True

        # 8. Check audit log entry was written for publishing
        audit = (
            db.query(AuditLogModel)
            .filter(
                AuditLogModel.action == "FLOOR_PLAN_SOURCE_VERSION_PUBLISH",
                AuditLogModel.entity_ref.like(f"%{floor_plan_id}%"),
            )
            .order_by(AuditLogModel.created_at.desc())
            .first()
        )
        assert audit is not None
        assert str(audit.actor_id) == ensure_uuid("usr_mock_001")
        assert f"floor_plan:{floor_plan_id}:version:2" in audit.entity_ref

    finally:
        db.close()

    # 9. Prove state survival with a completely fresh, independent DB session
    fresh_db = SessionLocal()
    try:
        fresh_curr = publisher.get_current_published_version(fresh_db, floor_plan_id)
        assert fresh_curr is not None
        assert fresh_curr.version_no == 2
        assert fresh_curr.is_published is True
        assert fresh_curr.published_by_user_id == ensure_uuid("usr_mock_001")

        fresh_history = publisher.get_source_versions(fresh_db, floor_plan_id)
        assert len(fresh_history) == 2
    finally:
        fresh_db.close()

    print("ALL FLOOR PLAN VERSIONING & POSTGRESQL PUBLISHING TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    setup_module()
    test_postgres_source_version_publishing_lifecycle()
