"""
Orientation Rule (Task 4.2 - Rule 17 - SOFT RULE).
Evaluates soft orientation preferences (e.g. reception facing entrance, workstation grid alignment).
Contributes penalty score without invalidating layout.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class OrientationRule(BaseRule):
    """Soft rule evaluating preferred furniture orientation angles."""

    def __init__(self):
        super().__init__(rule_id="orientation", severity=ViolationSeverity.WARNING_SOFT)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []

        for obj in layout.placed_objects:
            pref_rot = obj.custom_metadata.get("preferred_rotation_deg")
            if pref_rot is not None:
                diff = abs(obj.rotation_deg - pref_rot) % 360.0
                if diff > 15.0 and diff < 345.0:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=f"Object '{obj.id}' ({obj.item_type}) orientation {obj.rotation_deg}° deviates from preferred {pref_rot}°.",
                            affected_object_ids=[obj.id],
                            penalty_score=5.0,
                        )
                    )

        return violations
