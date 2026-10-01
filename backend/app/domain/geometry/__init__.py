"""Geometry validation domain models, canonical BIM entities, and schemas."""
from app.domain.geometry.schemas import ValidationResult, ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.geometry.entities import (
    EntityType,
    WallEntity,
    DoorEntity,
    WindowEntity,
    ColumnEntity,
    BeamEntity,
    RoomEntity,
    CanonicalFloorPlan,
)

__all__ = [
    "ValidationResult",
    "ConstraintViolation",
    "ViolationSeverity",
    "ViolationType",
    "EntityType",
    "WallEntity",
    "DoorEntity",
    "WindowEntity",
    "ColumnEntity",
    "BeamEntity",
    "RoomEntity",
    "CanonicalFloorPlan",
]
