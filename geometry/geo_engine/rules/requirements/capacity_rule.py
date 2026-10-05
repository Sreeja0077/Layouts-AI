"""
Capacity Rule (Task 4.2 - Rule 13).
Validates requested functional seat capacity (target_density_seats) against actual layout seat capacity.
Aligned strictly with RequirementSet domain schema.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class CapacityRule(BaseRule):
    """Verifies headcount seating capacity against requirement target_density_seats."""

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
        if not requirements or not requirements.target_density_seats or requirements.target_density_seats <= 0:
            return violations

        target_headcount = requirements.target_density_seats
        achieved_seats = layout.metrics.total_seats if layout.metrics else 0

        # Fallback capacity count if metrics total_seats is 0
        if achieved_seats == 0:
            for obj in layout.placed_objects:
                seats_attr = obj.custom_metadata.get("capacity", 1)
                achieved_seats += seats_attr

        if achieved_seats < target_headcount:
            deficit = target_headcount - achieved_seats
            violations.append(
                self.create_violation(
                    violation_type=ViolationType.SPACING_VIOLATION,
                    message=f"Layout total seating capacity ({achieved_seats} seats) is below required target density ({target_headcount} seats). Shortage: {deficit} seats.",
                    affected_element_type="HEADCOUNT_CAPACITY",
                )
            )

        return violations
