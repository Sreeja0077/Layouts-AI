"""
Wall Proximity Rule (Task 4.2 - Rule 19 - SOFT RULE).
Evaluates configurable minimum gap distance between furniture items (e.g., storage cabinets) and perimeter walls.
Contributes soft penalty score without invalidating layout.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class WallProximityRule(BaseRule):
    """Soft rule checking furniture wall alignment and gap preferences."""

    def __init__(self):
        super().__init__(rule_id="wall_proximity", severity=ViolationSeverity.WARNING_SOFT)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        if not room or not room.boundary_polygon or len(room.boundary_polygon) < 3:
            return violations

        cfg = get_ruleset_config(config)
        min_gap_m = (cfg.get("storage", {}).get("min_wall_gap_mm", 50)) / 1000.0
        room_poly = Polygon(room.boundary_polygon)

        for obj in layout.placed_objects:
            if "storage" in obj.item_type.lower() or "cabinet" in obj.item_type.lower():
                obj_poly = CollisionRule.get_object_polygon(obj)
                dist_to_wall = room_poly.exterior.distance(obj_poly)

                if dist_to_wall < min_gap_m and dist_to_wall > 0.001:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=f"Storage object '{obj.id}' ({obj.item_type}) gap to wall is {dist_to_wall*1000:.0f}mm (below target {min_gap_m*1000:.0f}mm).",
                            affected_object_ids=[obj.id],
                            penalty_score=2.0,
                        )
                    )
        return violations
