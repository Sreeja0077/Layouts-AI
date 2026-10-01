"""
Door Swing Rule (Task 4.2 - Rule 9).
Ensures furniture does not occupy or intersect the configured 90° door swing arc polygon area.
"""

import math
from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import DoorEntity, RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion, PlacedObject
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class DoorSwingRule(BaseRule):
    """Verifies that no placed furniture overlaps door swing arc geometries."""

    def __init__(self):
        super().__init__(rule_id="door_swing", severity=ViolationSeverity.CRITICAL_HARD)

    @staticmethod
    def get_door_swing_polygon(door: DoorEntity) -> Polygon:
        """Construct 90-degree door swing arc polygon if precalculated coords missing."""
        r = door.width_m if door.width_m > 0 else 0.9
        center_x, center_y = door.center_x, door.center_y
        base_angle = door.swing_deg

        vertices = [(center_x, center_y)]
        for step in range(11):
            angle = math.radians(base_angle + (step / 10.0) * 90.0)
            vx = center_x + r * math.cos(angle)
            vy = center_y + r * math.sin(angle)
            vertices.append((round(vx, 3), round(vy, 3)))
        return Polygon(vertices)

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
                if obj_poly.intersects(swing_poly):
                    inter = obj_poly.intersection(swing_poly)
                    if inter.area > 1e-3:
                        coords = list(inter.exterior.coords) if hasattr(inter, "exterior") else None
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.DOOR_SWING_OBSTRUCTION,
                                message=f"Object '{obj.id}' ({obj.item_type}) obstructs 90° door swing arc of Door '{door.id}'.",
                                affected_object_ids=[obj.id],
                                affected_element_type="DOOR",
                                overlap_polygon_coords=coords,
                            )
                        )
        return violations
