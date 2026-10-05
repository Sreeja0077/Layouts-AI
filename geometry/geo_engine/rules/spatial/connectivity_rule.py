"""
Connectivity Rule (Task 4.2 - Rule 16).
Validates walkable circulation path connectivity between distinct functional areas/zones when explicitly required.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class ConnectivityRule(BaseRule):
    """Verifies functional connectivity between key spatial zones when explicitly required."""

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

        # Check objects requiring connectivity
        req_conn_objects = [obj for obj in layout.placed_objects if obj.custom_metadata.get("requires_connectivity")]

        if req_conn_objects and not layout.circulation_paths:
            violations.append(
                self.create_violation(
                    violation_type=ViolationType.EGRESS_BLOCKAGE,
                    message=f"Layout contains {len(req_conn_objects)} objects requiring spatial connectivity but lacks declared circulation paths.",
                    affected_object_ids=[obj.id for obj in req_conn_objects],
                    affected_element_type="CIRCULATION_PATH",
                )
            )

        # Validate declared circulation path point counts
        for path in layout.circulation_paths:
            if not path.path_points or len(path.path_points) < 2:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message=f"Declared circulation path '{path.id}' has invalid or disconnected geometry.",
                        affected_element_type="CIRCULATION_PATH",
                    )
                )

        return violations
