"""
Collision Rule (Task 4.2 - Rule 2).
Detects 2D polygon overlaps between placed furniture instances, structural columns, and retained existing furniture.
"""

import math
from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion, PlacedObject
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class CollisionRule(BaseRule):
    """Detects 2D polygon overlaps between placed furniture, structural columns, and retained existing furniture."""

    def __init__(self):
        super().__init__(rule_id="collision", severity=ViolationSeverity.CRITICAL_HARD)

    @staticmethod
    def get_object_polygon(obj: PlacedObject) -> Polygon:
        """Calculate 2D rotated bounding polygon for a PlacedObject."""
        hw, hh = obj.width / 2.0, obj.height / 2.0
        local_vertices = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        rad = math.radians(obj.rotation_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        world_vertices = []
        for vx, vy in local_vertices:
            rx = vx * cos_a - vy * sin_a + obj.x
            ry = vx * sin_a + vy * cos_a + obj.y
            world_vertices.append((rx, ry))
        return Polygon(world_vertices)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        objects = layout.placed_objects
        n = len(objects)

        polygons = [self.get_object_polygon(obj) for obj in objects]

        # A. Placed Object vs Placed Object Collision
        for i in range(n):
            for j in range(i + 1, n):
                obj_a, obj_b = objects[i], objects[j]

                policy_a = obj_a.custom_metadata.get("collision_policy", "strict")
                policy_b = obj_b.custom_metadata.get("collision_policy", "strict")

                if policy_a == "attached" or policy_b == "attached":
                    continue

                poly_a, poly_b = polygons[i], polygons[j]

                if poly_a.intersects(poly_b):
                    inter = poly_a.intersection(poly_b)
                    if inter.area > 1e-4:  # Ignore trivial boundary touching
                        coords = self.extract_overlap_coords(inter)
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.COLLISION,
                                message=f"Object '{obj_a.id}' ({obj_a.item_type}) overlaps with object '{obj_b.id}' ({obj_b.item_type}) by {inter.area:.3f} sqm.",
                                affected_object_ids=[obj_a.id, obj_b.id],
                                overlap_polygon_coords=coords,
                            )
                        )

        # B. Placed Object vs Structural Columns Collision
        if room and room.columns:
            for col in room.columns:
                col_poly = Polygon(col.get_obstacle_polygon())
                for i, obj in enumerate(objects):
                    if polygons[i].intersects(col_poly):
                        inter = polygons[i].intersection(col_poly)
                        if inter.area > 1e-4:
                            coords = self.extract_overlap_coords(inter)
                            violations.append(
                                self.create_violation(
                                    violation_type=ViolationType.COLUMN_COLLISION,
                                    message=f"Object '{obj.id}' ({obj.item_type}) collides with structural Column '{col.id}' by {inter.area:.3f} sqm.",
                                    affected_object_ids=[obj.id],
                                    affected_element_type="COLUMN",
                                    overlap_polygon_coords=coords,
                                )
                            )

        # C. Placed Object vs Retained Existing Furniture Collision
        if room and room.existing_furniture:
            for ef in room.existing_furniture:
                if not ef.keep_flag:
                    continue
                # If ef is not the placed object itself
                ef_poly = Polygon([
                    (ef.position[0] - 0.4, ef.position[1] - 0.4),
                    (ef.position[0] + 0.4, ef.position[1] - 0.4),
                    (ef.position[0] + 0.4, ef.position[1] + 0.4),
                    (ef.position[0] - 0.4, ef.position[1] + 0.4),
                ])
                for i, obj in enumerate(objects):
                    if obj.id == ef.id:
                        continue
                    if polygons[i].intersects(ef_poly):
                        inter = polygons[i].intersection(ef_poly)
                        if inter.area > 1e-4:
                            coords = self.extract_overlap_coords(inter)
                            violations.append(
                                self.create_violation(
                                    violation_type=ViolationType.COLLISION,
                                    message=f"Object '{obj.id}' ({obj.item_type}) collides with retained existing furniture '{ef.id}'.",
                                    affected_object_ids=[obj.id, ef.id],
                                    overlap_polygon_coords=coords,
                                )
                            )

        return violations
