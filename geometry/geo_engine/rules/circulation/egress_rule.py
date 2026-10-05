"""
Egress Rule (Task 4.2 - Rule 8).
Verifies door threshold spatial egress access and declared circulation path connectivity to room exits.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import LineString, Point
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class EgressRule(BaseRule):
    """Evaluates door threshold spatial egress access and path connectivity to room exits."""

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

        door_points = [Point(d.center_x, d.center_y) for d in room.doors]
        if not door_points:
            return violations

        object_polys = [CollisionRule.get_object_polygon(obj) for obj in layout.placed_objects]

        # 1. Check physical furniture obstruction in immediate door egress zone (0.8m radius)
        for door_idx, door_pt in enumerate(door_points):
            door_obj = room.doors[door_idx]
            egress_zone = door_pt.buffer(0.8)
            for i, obj_poly in enumerate(object_polys):
                if obj_poly.intersects(egress_zone):
                    inter = obj_poly.intersection(egress_zone)
                    if inter.area > 0.05:
                        obj = layout.placed_objects[i]
                        coords = self.extract_overlap_coords(inter)
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.EGRESS_BLOCKAGE,
                                message=f"Object '{obj.id}' ({obj.item_type}) obstructs egress threshold of Door '{door_obj.id}'.",
                                affected_object_ids=[obj.id],
                                affected_element_type="DOOR",
                                overlap_polygon_coords=coords,
                            )
                        )

        # 2. Check that declared circulation paths connect to at least one door threshold (within 2.0m)
        # Note: Task 4.2 performs a deterministic spatial pre-check of door egress thresholds and declared circulation path LineString proximity. Full navigable seat-to-exit visibility graph and A* pathfinding validation belongs to Task 9.4.
        if layout.circulation_paths:
            connected = False
            for path in layout.circulation_paths:
                if not path.path_points:
                    continue
                if len(path.path_points) >= 2:
                    path_geom = LineString(path.path_points)
                else:
                    path_geom = Point(path.path_points[0])

                if any(path_geom.distance(door_pt) <= 2.0 for door_pt in door_points):
                    connected = True
                    break

            if not connected:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message="Declared circulation paths fail to connect within 2.0m of any room exit door.",
                        affected_element_type="CIRCULATION_PATH",
                    )
                )

        return violations
