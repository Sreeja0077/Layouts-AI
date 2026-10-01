"""
Window Obstruction Rule (Task 4.2 - Rule 18 - SOFT RULE).
Detects tall furniture (e.g. storage cabinets > 1.4m height) directly blocking windows.
Contributes soft penalty score without invalidating layout.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Point, Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule


class WindowObstructionRule(BaseRule):
    """Soft design rule detecting tall furniture placement blocking windows."""

    def __init__(self):
        super().__init__(rule_id="window_obstruction", severity=ViolationSeverity.WARNING_SOFT)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        if not room or not room.windows:
            return violations

        cfg = get_ruleset_config(config)
        win_cfg = cfg.get("windows", {})
        tall_threshold_mm = win_cfg.get("tall_object_height_threshold_mm", 1400)

        for win in room.windows:
            win_cx = (win.start_point[0] + win.end_point[0]) / 2.0
            win_cy = (win.start_point[1] + win.end_point[1]) / 2.0
            win_buffer = Point(win_cx, win_cy).buffer(0.8)

            for obj in layout.placed_objects:
                obj_height_mm = obj.custom_metadata.get("height_mm", 750)
                height_class = obj.custom_metadata.get("height_class", "low")

                if obj_height_mm >= tall_threshold_mm or height_class == "tall":
                    obj_poly = CollisionRule.get_object_polygon(obj)
                    if obj_poly.intersects(win_buffer):
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.WINDOW_OBSTRUCTION,
                                message=f"Tall object '{obj.id}' ({obj.item_type}) blocks window '{win.id}' natural light corridor.",
                                affected_object_ids=[obj.id],
                                affected_element_type="WINDOW",
                                penalty_score=10.0,
                            )
                        )
        return violations
