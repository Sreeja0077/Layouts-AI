"""
Clearance Rule (Task 4.2 - Rule 5).
Ensures sufficient clearance buffers behind chairs, in front of workstations/cabinets, using configurable ruleset thresholds and object rotation.
"""

import math
from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion, PlacedObject
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class ClearanceRule(BaseRule):
    """Verifies that furniture clearance zones (rear, front, side buffers) do not overlap inappropriately with other objects."""

    def __init__(self):
        super().__init__(rule_id="clearance", severity=ViolationSeverity.CRITICAL_HARD)

    @staticmethod
    def get_clearance_polygon(obj: PlacedObject, config: Dict[str, Any]) -> Polygon:
        """Construct 2D rotated clearance polygon around an object."""
        furniture_cfg = config.get("furniture", {})
        chair_clearance_m = furniture_cfg.get("chair_clearance_mm", 800) / 1000.0

        # Expand bounding dimensions by clearance buffers
        clear_width = obj.width + (obj.clearance_sides * 2.0)
        clear_height = obj.height + obj.clearance_front + max(obj.clearance_back, chair_clearance_m)

        hw, hh = clear_width / 2.0, clear_height / 2.0
        local_vertices = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]

        # Rotate to object world coordinates
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
        cfg = get_ruleset_config(config)
        objects = layout.placed_objects
        n = len(objects)

        clearance_polys = [self.get_clearance_polygon(obj, cfg) for obj in objects]
        object_polys = [CollisionRule.get_object_polygon(obj) for obj in objects]

        reported_pairs = set()

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                pair_key = (min(objects[i].id, objects[j].id), max(objects[i].id, objects[j].id))

                # Check if physical object B overlaps object A's required clearance zone
                if object_polys[j].intersects(clearance_polys[i]):
                    inter = object_polys[j].intersection(clearance_polys[i])
                    if inter.area > 1e-3:
                        if pair_key not in reported_pairs:
                            reported_pairs.add(pair_key)
                            coords = self.extract_overlap_coords(inter)
                            violations.append(
                                self.create_violation(
                                    violation_type=ViolationType.CLEARANCE_OVERLAP,
                                    message=f"Object '{objects[j].id}' ({objects[j].item_type}) obstructs required clearance zone of '{objects[i].id}' ({objects[i].item_type}).",
                                    affected_object_ids=[objects[i].id, objects[j].id],
                                    overlap_polygon_coords=coords,
                                )
                            )

        return violations
