"""
Base Rule Interface for Layout Validation Engine.
All 20 deterministic rules inherit from BaseRule and return structured ConstraintViolation objects.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet


class BaseRule(ABC):
    """Abstract base class for all deterministic layout validation rules."""

    def __init__(self, rule_id: str, severity: ViolationSeverity):
        self.rule_id = rule_id
        self.severity = severity

    @abstractmethod
    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        """
        Evaluate layout against this rule (Read-only, zero side effects).

        Returns:
            List of ConstraintViolation objects (empty list if rule passes).
        """
        pass

    def create_violation(
        self,
        violation_type: ViolationType,
        message: str,
        affected_object_ids: Optional[List[str]] = None,
        affected_element_type: Optional[str] = None,
        penalty_score: float = 0.0,
        overlap_polygon_coords: Optional[List[tuple]] = None,
    ) -> ConstraintViolation:
        """Helper to construct a standard ConstraintViolation object."""
        return ConstraintViolation(
            id=f"{self.rule_id}_{uuid4().hex[:8]}",
            violation_type=violation_type,
            severity=self.severity,
            affected_object_ids=affected_object_ids or [],
            affected_element_type=affected_element_type,
            message=message,
            penalty_score=penalty_score if self.severity == ViolationSeverity.WARNING_SOFT else 0.0,
            overlap_polygon_coords=overlap_polygon_coords,
        )
