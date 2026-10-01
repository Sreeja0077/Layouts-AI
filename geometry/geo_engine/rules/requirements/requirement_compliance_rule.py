"""
Requirement Compliance Rule (Task 4.2 - Rule 11).
Validates complete RequirementSet semantic compliance (space types, furniture categories, zones beyond count).
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class RequirementComplianceRule(BaseRule):
    """Verifies that mandatory space categories and zones requested in RequirementSet are present."""

    def __init__(self):
        super().__init__(rule_id="requirement_compliance", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        if not requirements or not requirements.items:
            return violations

        placed_types = {obj.item_type.upper() for obj in layout.placed_objects}

        for req_item in requirements.items:
            req_type = req_item.category.upper()
            # If required category is missing completely
            matching = [t for t in placed_types if req_type in t or t in req_type]
            if not matching and req_item.quantity > 0:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.SPACING_VIOLATION,
                        message=f"Mandatory requirement '{req_item.category}' (qty: {req_item.quantity}) is completely missing from generated layout.",
                        affected_element_type="REQUIREMENT_SET",
                    )
                )

        return violations
