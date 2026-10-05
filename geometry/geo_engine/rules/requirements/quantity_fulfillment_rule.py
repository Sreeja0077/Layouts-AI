"""
Quantity Fulfillment Rule (Task 4.2 - Rule 12).
Validates requested vs placed item quantities with configurable partial fulfillment modes (reject, warning, allow).
Aligned strictly with RequirementItem domain schema.
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

        # Tally placed items by catalog_item_id
        placed_counts: Dict[str, int] = {}
        for obj in layout.placed_objects:
            cid = obj.catalog_item_id or obj.item_type
            placed_counts[cid] = placed_counts.get(cid, 0) + 1

        for req_item in requirements.items:
            target_id = req_item.resolved_catalog_item_id or req_item.raw_phrase
            if not target_id or req_item.quantity <= 0:
                continue

            target_qty = req_item.quantity
            actual_qty = 0

            # Deterministic matching strictly on resolved_catalog_item_id
            if req_item.resolved_catalog_item_id:
                actual_qty = placed_counts.get(req_item.resolved_catalog_item_id, 0)
            else:
                # When resolved_catalog_item_id is absent, skip catalog matching
                continue

            if actual_qty < target_qty:
                missing = target_qty - actual_qty
                msg = f"Partial fulfillment for '{target_id}': requested {target_qty}, placed {actual_qty} (missing {missing})."

                if mode == "reject":
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=msg,
                            affected_element_type="QUANTITY",
                            severity=ViolationSeverity.CRITICAL_HARD,
                        )
                    )
                elif mode == "warning":
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=msg,
                            affected_element_type="QUANTITY",
                            penalty_score=float(missing * 0.1),
                            severity=ViolationSeverity.WARNING_SOFT,
                        )
                    )
                # mode == "allow" -> no violation

        return violations
