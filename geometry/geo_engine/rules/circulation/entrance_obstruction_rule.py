"""
Entrance Obstruction Rule (Task 4.2 - Rule 10).
Ensures furniture does not block door thresholds or immediate entrance approach clearance areas.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Point
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class EntranceObstructionRule(BaseRule):
    """Verifies that furniture does not obstruct immediate entrance threshold approach zones."""

    def __init__(self):
        super().__init__(rule_id="entrance_obstruction", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        if not room or not room.doors:
            return violations

        cfg = get_ruleset_config(config)
        door_cfg = cfg.get("doors", {})
        approach_m = door_cfg.get("entrance_approach_clearance_mm", 1000) / 1000.0

        for door in room.doors:
            approach_circle = Point(door.center_x, door.center_y).buffer(approach_m)

            for obj in layout.placed_objects:
                obj_poly = CollisionRule.get_object_polygon(obj)
                if obj_poly.intersects(approach_circle):
                    inter = obj_poly.intersection(approach_circle)
                    if inter.area > 0.05:
                        coords = self.extract_overlap_coords(inter)
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.CLEARANCE_OVERLAP,
                                message=f"Object '{obj.id}' ({obj.item_type}) blocks {approach_m}m immediate entrance approach to Door '{door.id}'.",
                                affected_object_ids=[obj.id],
                                affected_element_type="DOOR",
                                overlap_polygon_coords=coords,
                            )
                        )

        return violations
