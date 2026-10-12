"""
Fixed Object Integrity Rule (Task 4.2 - Rule 4).
Ensures existing retained furniture items (keep_flag=True) are preserved, not moved, not rotated, and not removed by AI layout proposals.
Aligned with authoritative ExistingFurnitureEntity schema.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class FixedObjectIntegrityRule(BaseRule):
    """Guards existing retained furniture instances (keep_flag=True) from unauthorized changes or removal."""

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

        if not room or not room.existing_furniture:
            return violations

        # Filter fixed/sold existing furniture (SOLD_FIXED or keep_flag=True when not AVAILABLE_MOVABLE)
        from app.domain.geometry.entities import MovabilityStatus

        def is_fixed(ef) -> bool:
            status = getattr(ef, "movability_status", None)
            if status == MovabilityStatus.SOLD_FIXED or status == "SOLD_FIXED":
                return True
            if status == MovabilityStatus.AVAILABLE_MOVABLE or status == "AVAILABLE_MOVABLE":
                return False
            # Default fallback: if keep_flag is explicitly set
            return bool(getattr(ef, "keep_flag", True))

        fixed_map = {ef.id: ef for ef in room.existing_furniture if is_fixed(ef)}
        if not fixed_map:
            return violations

        # Placed map by id or source_object_id
        placed_map = {}
        for obj in layout.placed_objects:
            placed_map[obj.id] = obj
            if getattr(obj, "source_object_id", None):
                placed_map[obj.source_object_id] = obj

        for ef_id, ef in fixed_map.items():
            if ef_id not in placed_map:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.COLLISION,
                        message=f"Fixed/Sold existing furniture '{ef_id}' (catalog: '{ef.catalog_item_id}') was missing/removed from layout.",
                        affected_object_ids=[ef_id],
                        affected_element_type="EXISTING_FURNITURE",
                    )
                )
            else:
                obj = placed_map[ef_id]
                orig_x, orig_y = ef.position[0], ef.position[1]
                dx = abs(obj.x - orig_x)
                dy = abs(obj.y - orig_y)
                rot_diff = abs((obj.rotation_deg - ef.rotation) % 360.0)
                rot_diff = min(rot_diff, 360.0 - rot_diff)

                if dx > 1e-3 or dy > 1e-3 or rot_diff > 1e-3:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.COLLISION,
                            message=f"Fixed/Sold furniture '{ef_id}' position/rotation was altered from ({orig_x}, {orig_y}, {ef.rotation}°) to ({obj.x}, {obj.y}, {obj.rotation_deg}°).",
                            affected_object_ids=[obj.id],
                            affected_element_type="EXISTING_FURNITURE",
                        )
                    )

        return violations
