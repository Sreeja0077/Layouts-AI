"""
Natural Light Rule (Task 4.2 - Rule 20 - SOFT RULE).
Evaluates geometric heuristic proximity of workstations to windows for natural daylight access.
Contributes soft penalty score without invalidating layout.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Point
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config


class NaturalLightRule(BaseRule):
    """Soft design heuristic scoring workstation access to natural daylight."""

    def __init__(self):
        super().__init__(rule_id="natural_light", severity=ViolationSeverity.WARNING_SOFT)

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
        max_dist_m = cfg.get("windows", {}).get("natural_light_max_distance_mm", 6000) / 1000.0
        win_points = [
            Point((w.start_point[0] + w.end_point[0]) / 2.0, (w.start_point[1] + w.end_point[1]) / 2.0)
            for w in room.windows
        ]

        for obj in layout.placed_objects:
            if "desk" in obj.item_type.lower() or "workstation" in obj.item_type.lower():
                obj_pt = Point(obj.x, obj.y)
                min_win_dist = min(wp.distance(obj_pt) for wp in win_points)

                if min_win_dist > max_dist_m:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.WINDOW_OBSTRUCTION,
                            message=f"Workstation '{obj.id}' ({obj.item_type}) is {min_win_dist:.1f}m from nearest window (exceeds preferred {max_dist_m:.1f}m daylight radius).",
                            affected_object_ids=[obj.id],
                            affected_element_type="WINDOW",
                            penalty_score=3.0,
                        )
                    )
        return violations
