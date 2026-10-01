"""
Quantity Fulfillment Rule (Task 4.2 - Rule 12).
Validates requested vs placed item quantities with configurable partial fulfillment modes (reject, warning, allow).
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config


class QuantityFulfillmentRule(BaseRule):
    """Checks requested vs placed item counts with structured partial fulfillment reporting."""

    def __init__(self):
        super().__init__(rule_id="quantity_fulfillment", severity=ViolationSeverity.CRITICAL_HARD)

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

        cfg = get_ruleset_config(config)
        mode = cfg.get("quantity", {}).get("partial_fulfillment", {}).get("mode", "warning")

        # Tally placed items by category
        placed_counts: Dict[str, int] = {}
        for obj in layout.placed_objects:
            cat = obj.item_type.upper()
            placed_counts[cat] = placed_counts.get(cat, 0) + 1

        for req_item in requirements.items:
            req_cat = req_item.category.upper()
            target_qty = req_item.quantity

            # Sum placed items matching category
            actual_qty = sum(count for cat, count in placed_counts.items() if req_cat in cat or cat in req_cat)

            if actual_qty < target_qty:
                missing = target_qty - actual_qty
                msg = f"Partial fulfillment for '{req_item.category}': requested {target_qty}, placed {actual_qty} (missing {missing})."

                if mode == "reject":
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=msg,
                            affected_element_type="QUANTITY",
                        )
                    )
                elif mode == "warning":
                    # Emit warning violation with penalty
                    v = self.create_violation(
                        violation_type=ViolationType.SPACING_VIOLATION,
                        message=msg,
                        affected_element_type="QUANTITY",
                        penalty_score=float(missing * 0.1),
                    )
                    v.severity = ViolationSeverity.WARNING_SOFT
                    violations.append(v)

        return violations
