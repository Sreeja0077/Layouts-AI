"""
Orientation Rule (Task 4.2 - Rule 17 - SOFT RULE).
Evaluates soft orientation preferences using true circular angular difference math.
Contributes penalty score without invalidating layout.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class OrientationRule(BaseRule):
    """Soft rule evaluating preferred furniture orientation angles with true circular angle math."""

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
                diff_raw = abs((obj.rotation_deg - pref_rot) % 360.0)
                diff = min(diff_raw, 360.0 - diff_raw)
                if diff > 15.0:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=f"Object '{obj.id}' ({obj.item_type}) orientation {obj.rotation_deg}° deviates from preferred {pref_rot}° by {diff:.1f}°.",
                            affected_object_ids=[obj.id],
                            penalty_score=5.0,
                        )
                    )

        return violations
