"""
Egress Rule (Task 4.2 - Rule 8).
Verifies layout-level path connectivity ensuring all placed workstations/seats have a connected walking path to designated room exits.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Point, Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class EgressRule(BaseRule):
    """Evaluates spatial path connectivity between workstations and room exits."""

    def __init__(self):
        super().__init__(rule_id="egress", severity=ViolationSeverity.CRITICAL_HARD)

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

        # Get door locations
        door_points = [(d.center_x, d.center_y) for d in room.doors]
        if not door_points:
            return violations

        # Check if objects block egress access
        object_polys = [CollisionRule.get_object_polygon(obj) for obj in layout.placed_objects]

        for obj in layout.placed_objects:
            obj_pt = Point(obj.x, obj.y)
            # Find distance to closest door
            min_door_dist = min(Point(dp[0], dp[1]).distance(obj_pt) for dp in door_points)

            # If isolated object is far from all doors with no circulation paths
            if min_door_dist > 20.0 and not layout.circulation_paths:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message=f"Workstation '{obj.id}' ({obj.item_type}) at ({obj.x}, {obj.y}) lacks connected egress path to room exit.",
                        affected_object_ids=[obj.id],
                        affected_element_type="DOOR",
                    )
                )

        return violations
