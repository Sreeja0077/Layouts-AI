"""
Door Swing Rule (Task 4.2 - Rule 9).
Ensures furniture does not occupy or intersect the door swing arc polygon area derived from canonical DoorEntity.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import DoorEntity, RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class DoorSwingRule(BaseRule):
    """Verifies that no placed furniture overlaps canonical door swing arc geometries."""

    def __init__(self):
        super().__init__(rule_id="door_swing", severity=ViolationSeverity.CRITICAL_HARD)

    @staticmethod
    def get_door_swing_polygon(door: DoorEntity) -> Polygon:
        """Construct door swing arc polygon using canonical DoorEntity swing arc method."""
        vertices = door.get_swing_arc_polygon()
        if len(vertices) >= 3:
            return Polygon(vertices)
        return Polygon()

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

        door_swings = [(door, self.get_door_swing_polygon(door)) for door in room.doors]

        for obj in layout.placed_objects:
            obj_poly = CollisionRule.get_object_polygon(obj)

            for door, swing_poly in door_swings:
                if swing_poly.is_empty:
                    continue
                if obj_poly.intersects(swing_poly):
                    inter = obj_poly.intersection(swing_poly)
                    if inter.area > 1e-3:
                        coords = self.extract_overlap_coords(inter)
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.DOOR_SWING_OBSTRUCTION,
                                message=f"Object '{obj.id}' ({obj.item_type}) obstructs door swing arc of Door '{door.id}'.",
                                affected_object_ids=[obj.id],
                                affected_element_type="DOOR",
                                overlap_polygon_coords=coords,
                            )
                        )
        return violations
