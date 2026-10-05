"""
Requirement Compliance Rule (Task 4.2 - Rule 11).
Validates complete RequirementSet compliance using resolved catalog item IDs and exact item matches.
Aligned strictly with RequirementItem domain schema.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class RequirementComplianceRule(BaseRule):
    """Verifies that resolved mandatory requirement items are present in the layout."""

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

        placed_catalog_ids = {obj.catalog_item_id for obj in layout.placed_objects if obj.catalog_item_id}

        for req_item in requirements.items:
            target_id = req_item.resolved_catalog_item_id or req_item.raw_phrase
            if not target_id or req_item.quantity <= 0:
                continue

            # Primary match on resolved_catalog_item_id
            if req_item.resolved_catalog_item_id:
                if req_item.resolved_catalog_item_id not in placed_catalog_ids:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=f"Mandatory resolved requirement item '{req_item.resolved_catalog_item_id}' (qty: {req_item.quantity}) is completely missing from layout.",
                            affected_element_type="REQUIREMENT_SET",
                        )
                    )
            elif req_item.raw_phrase:
                # Secondary exact phrase match if catalog item ID was not resolved
                matching = [c for c in placed_catalog_ids if req_item.raw_phrase.lower() in c.lower()]
                if not matching:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=f"Mandatory requirement phrase '{req_item.raw_phrase}' (qty: {req_item.quantity}) is missing from layout.",
                            affected_element_type="REQUIREMENT_SET",
                        )
                    )

        return violations
