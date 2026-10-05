"""
SQLAlchemy ORM models for PostgreSQL + PostGIS database entities.
Defines entity mappings for Users, Projects, FloorPlans, FloorPlanSourceVersions, Regions,
FurnitureCatalogItems, RequirementSets, ClarificationQuestions, LayoutSuggestions, Revisions,
ValidationResults, Approvals, and AuditLogs.
Reconciled with schema_draft.sql & blueprint architecture.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Cross-dialect JSON and UUID types
JSONType = JSON().with_variant(JSONB, "postgresql")
UUIDType = String(36).with_variant(PG_UUID(as_uuid=True), "postgresql")

# PostGIS Geometry type
try:
    from geoalchemy2 import Geometry
    GeometryType = Geometry(geometry_type="POLYGON", srid=0, spatial_index=False).with_variant(JSONType, "sqlite")
except (ImportError, Exception):
    GeometryType = JSONType


class Base(DeclarativeBase):
    """Base Declarative Model Class."""
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    org_id: Mapped[str] = mapped_column(UUIDType, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255))
    org_id: Mapped[str] = mapped_column(UUIDType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    floor_plans: Mapped[List["FloorPlan"]] = relationship("FloorPlan", back_populates="project", cascade="all, delete-orphan")


class FloorPlan(Base):
    __tablename__ = "floor_plans"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    building_name: Mapped[Optional[str]] = mapped_column(String(255))
    floor_number: Mapped[int] = mapped_column(Integer, default=1)

    current_working_revision_id: Mapped[Optional[str]] = mapped_column(UUIDType)
    current_published_revision_id: Mapped[Optional[str]] = mapped_column(UUIDType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="floor_plans")
    regions: Mapped[List["Region"]] = relationship("Region", back_populates="floor_plan", cascade="all, delete-orphan")
    source_versions: Mapped[List["FloorPlanSourceVersionModel"]] = relationship("FloorPlanSourceVersionModel", back_populates="floor_plan", cascade="all, delete-orphan")


class FloorPlanSourceVersionModel(Base):
    __tablename__ = "floor_plan_source_versions"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    ifc_export_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    uploaded_by: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("users.id"))
    verification_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    verification_report: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType)
    reviewer_user_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("users.id"))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_by_user_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("users.id"))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="source_versions")

    __table_args__ = (
        UniqueConstraint("floor_plan_id", "version_no", name="uq_floor_plan_version_no"),
        Index(
            "uq_published_source_version",
            "floor_plan_id",
            unique=True,
            postgresql_where=text("is_published = true"),
            sqlite_where=text("is_published = 1"),
        ),
    )


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="Selected Region")
    polygon_geom: Mapped[Any] = mapped_column(GeometryType, nullable=False)
    polygon_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    area_sqm: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="regions")


class FurnitureCatalogItemModel(Base):
    __tablename__ = "furniture_catalog_items"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    width_m: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    height_m: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    clearance_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    aliases: Mapped[List[Any]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RequirementSetModel(Base):
    __tablename__ = "requirement_sets"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    region_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("regions.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    spec_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    clarification_questions: Mapped[List["ClarificationQuestionModel"]] = relationship("ClarificationQuestionModel", back_populates="requirement_set", cascade="all, delete-orphan")


class ClarificationQuestionModel(Base):
    __tablename__ = "clarification_questions"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_set_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("requirement_sets.id", ondelete="CASCADE"), nullable=False)
    question_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    user_answer: Mapped[Optional[str]] = mapped_column(Text)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    requirement_set: Mapped["RequirementSetModel"] = relationship("RequirementSetModel", back_populates="clarification_questions")


class LayoutSuggestionModel(Base):
    __tablename__ = "layout_suggestions"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    region_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("regions.id", ondelete="SET NULL"))
    strategy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    placed_objects_json: Mapped[List[Any]] = mapped_column(JSONType, default=list)
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Revision(Base):
    __tablename__ = "revisions"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    base_revision_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("revisions.id"))
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    operations_json: Mapped[List[Any]] = mapped_column(JSONType, default=list)
    snapshot_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType)
    created_by: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ValidationResultModel(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    revision_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("revisions.id", ondelete="CASCADE"))
    suggestion_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("layout_suggestions.id", ondelete="CASCADE"))
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violations_json: Mapped[List[Any]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    revision_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("revisions.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    details_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
