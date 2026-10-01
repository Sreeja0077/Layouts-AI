"""
Capacity Rule (Task 4.2 - Rule 13).
Validates requested functional seat capacity against actual layout seat capacity.
Distinguishes furniture piece count from seating capacity.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class CapacityRule(BaseRule):
    """Verifies headcount seating capacity against requirement target."""

    def __init__(self):
        super().__init__(rule_id="capacity", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        if not requirements or requirements.total_headcount <= 0:
            return violations

        target_headcount = requirements.total_headcount
        achieved_seats = layout.metrics.total_seats

        # Fallback count if metrics seats is 0
        if achieved_seats == 0:
            for obj in layout.placed_objects:
                seats_attr = obj.custom_metadata.get("capacity", 1)
                achieved_seats += seats_attr

        if achieved_seats < target_headcount:
            deficit = target_headcount - achieved_seats
            violations.append(
                self.create_violation(
                    violation_type=ViolationType.SPACING_VIOLATION,
                    message=f"Layout total seating capacity ({achieved_seats} seats) is below required headcount ({target_headcount} seats). Shortage: {deficit} seats.",
                    affected_element_type="HEADCOUNT_CAPACITY",
                )
            )

        return violations
