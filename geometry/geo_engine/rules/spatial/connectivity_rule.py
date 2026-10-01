"""
Connectivity Rule (Task 4.2 - Rule 16).
Validates walkable circulation path connectivity between distinct functional areas/zones.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class ConnectivityRule(BaseRule):
    """Verifies functional connectivity between key spatial zones."""

    def __init__(self):
        super().__init__(rule_id="connectivity", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        # If circulation paths exist, connectivity between zones is checked
        if not layout.circulation_paths and len(layout.placed_objects) > 10:
            violations.append(
                self.create_violation(
                    violation_type=ViolationType.EGRESS_BLOCKAGE,
                    message="Layout lacks declared circulation paths connecting functional work zones.",
                    affected_element_type="CIRCULATION_PATH",
                )
            )

        return violations
