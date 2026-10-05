"""
Floor Plan Source Versioning and Publishing Engine.
Manages PostgreSQL-backed FloorPlanSourceVersion publishing, version number tracking, and locked baseline snapshot points.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.persistence.models import FloorPlanSourceVersionModel, AuditLogModel
from app.security.auth import AuthenticatedUser


class FloorPlanSourceVersionPayload(BaseModel):
    """Payload representing a published floor plan source version baseline."""
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(..., description="Unique source version ID")
    floor_plan_id: str = Field(..., description="Associated floor plan ID")
    version_no: int = Field(..., ge=1, description="Sequential version number (1, 2, 3...)")
    source_type: str = Field(..., description="Source format ('IFC', 'DXF', 'PDF', 'RASTER_IMAGE')")
    file_name: str = Field(..., description="Original uploaded file name")
    file_storage_path: str = Field(..., description="Storage key reference")
    verification_status: str = Field("PENDING", description="Verification status ('PENDING', 'VERIFIED', 'REJECTED')")
    is_published: bool = Field(default=False, description="True if locked as published baseline")
    published_by_user_id: Optional[str] = Field(None, description="User ID of publisher")
    published_at: Optional[str] = Field(None, description="ISO timestamp of publishing")
    geometry_summary: Dict[str, Any] = Field(default_factory=dict, description="Verified room counts & boundaries")

    @classmethod
    def from_orm_model(cls, model: FloorPlanSourceVersionModel) -> "FloorPlanSourceVersionPayload":
        file_name = Path(model.file_storage_path).name if model.file_storage_path else "floor_plan"
        summary = model.verification_report if model.verification_report else {}
        return cls(
            version_id=str(model.id),
            floor_plan_id=str(model.floor_plan_id),
            version_no=model.version_no,
            source_type=model.source_type,
            file_name=file_name,
            file_storage_path=model.file_storage_path,
            verification_status=model.verification_status,
            is_published=model.is_published,
            published_by_user_id=str(model.published_by_user_id) if model.published_by_user_id else None,
            published_at=model.published_at.isoformat() if model.published_at else None,
            geometry_summary=summary,
        )


class SourceVersionPublisher:
    """Engine managing floor plan source versioning and publishing transitions backed by PostgreSQL."""

    def publish_version(
        self,
        db: Session,
        floor_plan_id: str,
        current_user: AuthenticatedUser,
        version_no: Optional[int] = None,
    ) -> FloorPlanSourceVersionPayload:
        """
        Publish an existing, verified floor plan source version stored in PostgreSQL.
        Enforces:
        - Source version existence (HTTP 404 if missing)
        - Verification status MUST be 'VERIFIED' (HTTP 400 if PENDING or REJECTED)
        - Publisher identity comes exclusively from authenticated current_user
        - User is provisioned in PostgreSQL users table
        - Unpublishes any previous published version for the floor plan
        - Atomically persists publication state & audit log in PostgreSQL
        """
        from app.api.v1.projects import ensure_uuid, ensure_user_exists

        fp_uuid = ensure_uuid(floor_plan_id)
        publisher_uuid = ensure_user_exists(db, current_user)

        query = db.query(FloorPlanSourceVersionModel).filter(
            FloorPlanSourceVersionModel.floor_plan_id == fp_uuid
        )

        if version_no is not None:
            query = query.filter(FloorPlanSourceVersionModel.version_no == version_no)

        record = query.order_by(FloorPlanSourceVersionModel.version_no.desc()).first()
        if not record:
            ver_desc = f"version {version_no}" if version_no is not None else "latest version"
            raise ValueError(f"Floor plan source version ({ver_desc}) not found for floor plan '{floor_plan_id}'")

        if record.verification_status != "VERIFIED":
            raise ValueError(
                f"Cannot publish floor plan source version '{record.version_no}' with verification_status '{record.verification_status}'. "
                "Geometry must be VERIFIED by Layouts Team before publishing."
            )

        # Idempotency check: if already published, return deterministic state without duplicate audit entries
        if record.is_published:
            return FloorPlanSourceVersionPayload.from_orm_model(record)

        # Unpublish any existing published source version for this floor plan
        db.query(FloorPlanSourceVersionModel).filter(
            FloorPlanSourceVersionModel.floor_plan_id == fp_uuid,
            FloorPlanSourceVersionModel.is_published == True,
        ).update({"is_published": False}, synchronize_session=False)

        # Mark target record as published
        now_dt = datetime.utcnow()
        record.is_published = True
        record.published_by_user_id = publisher_uuid
        record.published_at = now_dt

        # Audit log entry
        audit = AuditLogModel(
            id=str(uuid.uuid4()),
            actor_id=publisher_uuid,
            action="FLOOR_PLAN_SOURCE_VERSION_PUBLISH",
            entity_ref=f"floor_plan:{floor_plan_id}:version:{record.version_no}",
            details_json={
                "floor_plan_id": floor_plan_id,
                "version_no": record.version_no,
                "source_version_id": str(record.id),
                "publisher": current_user.user_id,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(record)

        return FloorPlanSourceVersionPayload.from_orm_model(record)

    def get_current_published_version(self, db: Session, floor_plan_id: str) -> Optional[FloorPlanSourceVersionPayload]:
        """Query PostgreSQL for currently published source version baseline for a floor plan."""
        from app.api.v1.projects import ensure_uuid
        fp_uuid = ensure_uuid(floor_plan_id)
        record = (
            db.query(FloorPlanSourceVersionModel)
            .filter(
                FloorPlanSourceVersionModel.floor_plan_id == fp_uuid,
                FloorPlanSourceVersionModel.is_published == True,
            )
            .first()
        )
        if not record:
            return None
        return FloorPlanSourceVersionPayload.from_orm_model(record)

    def get_source_versions(self, db: Session, floor_plan_id: str) -> List[FloorPlanSourceVersionPayload]:
        """List all persisted source versions in PostgreSQL for a floor plan ordered by version_no."""
        from app.api.v1.projects import ensure_uuid
        fp_uuid = ensure_uuid(floor_plan_id)
        records = (
            db.query(FloorPlanSourceVersionModel)
            .filter(FloorPlanSourceVersionModel.floor_plan_id == fp_uuid)
            .order_by(FloorPlanSourceVersionModel.version_no.asc())
            .all()
        )
        return [FloorPlanSourceVersionPayload.from_orm_model(r) for r in records]
