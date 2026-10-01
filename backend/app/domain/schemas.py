"""
Central domain schemas exporter for backend.app.domain.
Aggregates requirement, layout, and geometry validation contracts.
"""

from app.domain.requirements.schemas import (
    RequirementSet,
    RequirementItem,
    RequirementStatus,
    ResolutionMethod,
    SpatialPreference,
)
from app.domain.layout.schemas import (
    LayoutSuggestion,
    PlacedObject,
    CirculationPath,
    LayoutMetrics,
    LayoutAction,
    ActionType,
    Polygon2D,
    BoundingBox2D,
)
from app.domain.geometry.schemas import (
    ValidationResult,
    ConstraintViolation,
    ViolationSeverity,
    ViolationType,
)

__all__ = [
    "RequirementSet",
    "RequirementItem",
    "RequirementStatus",
    "ResolutionMethod",
    "SpatialPreference",
    "LayoutSuggestion",
    "PlacedObject",
    "CirculationPath",
    "LayoutMetrics",
    "LayoutAction",
    "ActionType",
    "Polygon2D",
    "BoundingBox2D",
    "ValidationResult",
    "ConstraintViolation",
    "ViolationSeverity",
    "ViolationType",
]
