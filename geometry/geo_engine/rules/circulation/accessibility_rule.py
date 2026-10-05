"""
Accessibility Rule (Task 4.2 - Rule 7).
Architectural spatial accessibility check evaluating accessible route widths and turning diameters against configurable ruleset thresholds.
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


class AccessibilityRule(BaseRule):
    """Verifies architectural accessibility route width and turning diameter clearance in circulation zones."""

    def __init__(self):
        super().__init__(rule_id="accessibility", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        cfg = get_ruleset_config(config)
        access_cfg = cfg.get("accessibility", {})

        route_min_m = access_cfg.get("accessible_route_min_mm", 900) / 1000.0
        turning_r_m = (access_cfg.get("turning_diameter_mm", 1500) / 1000.0) / 2.0

        object_polys = [CollisionRule.get_object_polygon(obj) for obj in layout.placed_objects]

        for path in layout.circulation_paths:
            if not path.path_points:
                continue

            # 1. Enforce accessible route minimum width
            if path.min_width_meters < route_min_m:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message=f"Circulation route '{path.id}' width ({path.min_width_meters:.2f}m) is below minimum accessible route threshold ({route_min_m:.2f}m).",
                        affected_element_type="CIRCULATION_PATH",
                    )
                )

            # 2. Check wheelchair turning circle clearance at path endpoints/nodes
            for pt in [path.path_points[0], path.path_points[-1]]:
                turning_circle = Point(pt[0], pt[1]).buffer(turning_r_m)
                for i, obj_poly in enumerate(object_polys):
                    if obj_poly.intersects(turning_circle):
                        inter = obj_poly.intersection(turning_circle)
                        if inter.area > 0.05:
                            obj = layout.placed_objects[i]
                            coords = self.extract_overlap_coords(inter)
                            violations.append(
                                self.create_violation(
                                    violation_type=ViolationType.CLEARANCE_OVERLAP,
                                    message=f"Object '{obj.id}' ({obj.item_type}) obstructs {turning_r_m * 2:.1f}m wheelchair turning clearance at circulation node ({pt[0]}, {pt[1]}).",
                                    affected_object_ids=[obj.id],
                                    affected_element_type="ACCESSIBILITY_TURNING_CIRCLE",
                                    overlap_polygon_coords=coords,
                                )
                            )

        return violations
