"""
Containment Rule (Task 4.2 - Rule 3).
Ensures furniture item footprints remain 100% inside usable room boundary (supports non-rectangular, concave, L-shaped, and rooms with interior column holes).
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.freespace import FreeSpaceEngine
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class ContainmentRule(BaseRule):
    """Verifies that all placed objects are completely contained inside usable room boundary."""

    def __init__(self):
        super().__init__(rule_id="containment", severity=ViolationSeverity.CRITICAL_HARD)

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

        column_obs = [col.get_obstacle_polygon() for col in (room.columns or [])]
        usable_geom = FreeSpaceEngine.compute_usable_geometry(
            room_polygon=room.boundary_polygon,
            obstacles=column_obs,
            wall_inset_buffer=0.0,
        )

        if usable_geom.is_empty:
            return violations

        for obj in layout.placed_objects:
            obj_poly = CollisionRule.get_object_polygon(obj)

            if not usable_geom.contains(obj_poly):
                outside_part = obj_poly.difference(usable_geom)
                outside_area = outside_part.area if not outside_part.is_empty else 0.0

                if outside_area > 1e-4:
                    coords = self.extract_overlap_coords(outside_part)
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.OUT_OF_BOUNDS,
                            message=f"Object '{obj.id}' ({obj.item_type}) extends outside usable room boundary by {outside_area:.3f} sqm.",
                            affected_object_ids=[obj.id],
                            affected_element_type="ROOM",
                            overlap_polygon_coords=coords,
                        )
                    )

        return violations
