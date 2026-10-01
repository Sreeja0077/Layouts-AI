"""
Fixed Object Integrity Rule (Task 4.2 - Rule 4).
Ensures existing/fixed/locked objects are not moved, rotated, or modified by AI layout proposals.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class FixedObjectIntegrityRule(BaseRule):
    """Guards existing/locked furniture instances from unauthorized changes."""

    def __init__(self):
        super().__init__(rule_id="fixed_object_integrity", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []

        # Compare placed objects against fixed/existing objects in room
        existing_furniture = getattr(room, "existing_furniture", [])
        if not existing_furniture:
            return violations

        # Index existing fixed furniture by ID
        fixed_map = {f.id: f for f in existing_furniture if getattr(f, "locked", False) or "fixed" in getattr(f, "tags", [])}

        for obj in layout.placed_objects:
            if obj.id in fixed_map:
                original = fixed_map[obj.id]
                # Check position change
                dx = abs(obj.x - original.x)
                dy = abs(obj.y - original.y)
                drot = abs(obj.rotation_deg - original.rotation_deg)

                if dx > 1e-3 or dy > 1e-3 or drot > 1e-3:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.COLLISION,
                            message=f"Fixed object '{obj.id}' position/rotation was altered from baseline ({original.x}, {original.y}, {original.rotation_deg}°) to ({obj.x}, {obj.y}, {obj.rotation_deg}°).",
                            affected_object_ids=[obj.id],
                        )
                    )

        return violations
