"""
SQLAlchemy ORM models for PostgreSQL + PostGIS database entities.
Defines entity mappings for projects, floor plans, regions, catalog items, requirements, revisions, and approvals.
Supports cross-dialect JSON and UUID handling for PostgreSQL (JSONB) and SQLite testing.
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
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Cross-dialect JSON type: uses JSONB on PostgreSQL, standard JSON on SQLite/others
JSONType = JSON().with_variant(JSONB, "postgresql")
UUIDType = String(36).with_variant(PG_UUID(as_uuid=True), "postgresql")


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


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255))
    org_id: Mapped[str] = mapped_column(UUIDType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

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

    project: Mapped["Project"] = relationship("Project", back_populates="floor_plans")
    regions: Mapped[List["Region"]] = relationship("Region", back_populates="floor_plan", cascade="all, delete-orphan")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="Selected Region")
    polygon_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    area_sqm: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    floor_plan: Mapped["FloorPlan"] = relationship("FloorPlan", back_populates="regions")


class RequirementSetModel(Base):
    __tablename__ = "requirement_sets"

    id: Mapped[str] = mapped_column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_plan_id: Mapped[str] = mapped_column(UUIDType, ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False)
    region_id: Mapped[Optional[str]] = mapped_column(UUIDType, ForeignKey("regions.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    spec_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


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
