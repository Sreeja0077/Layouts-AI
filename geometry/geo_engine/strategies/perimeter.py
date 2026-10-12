"""
Perimeter Strategy Template (Task 9.1 - Strategy 1).
Prioritizes furniture placement along room/region perimeter walls,
maximizing open internal floor space for central collaboration or meeting zones.
"""

import math
from typing import Any, Dict, List, Tuple
from geometry.geo_engine.strategies.base_strategy import StrategyTemplate


class PerimeterStrategy(StrategyTemplate):
    """Aligns furniture along walls and boundary margins."""

    def __init__(self):
        super().__init__(
            strategy_id="PERIMETER",
            name="Perimeter Alignment Strategy",
            description="Arranges desks and storage along the perimeter walls, leaving the central zone open.",
        )

    def get_anchoring_preference(self) -> str:
        return "PERIMETER"

    def score_slot(
        self,
        slot_x: float,
        slot_y: float,
        item: Dict[str, Any],
        context: Dict[str, Any],
    ) -> float:
        bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
        min_x, min_y, max_x, max_y = bounds

        # Distance to nearest boundary wall
        dist_to_wall = min(
            abs(slot_x - min_x),
            abs(max_x - slot_x),
            abs(slot_y - min_y),
            abs(max_y - slot_y),
        )

        # Manager preference: corner perimeter
        item_type = str(item.get("item_type", "")).upper()
        if "MANAGER" in item_type or "EXECUTIVE" in item_type or "CABIN" in item_type:
            # Score favors corners
            corner_dists = [
                math.hypot(slot_x - min_x, slot_y - min_y),
                math.hypot(slot_x - max_x, slot_y - min_y),
                math.hypot(slot_x - min_x, slot_y - max_y),
                math.hypot(slot_x - max_x, slot_y - max_y),
            ]
            return min(corner_dists) * 0.5 + dist_to_wall

        return dist_to_wall

    def get_orientation_preferences(
        self,
        item_type: str,
        slot_pos: Tuple[float, float],
        context: Dict[str, Any],
    ) -> List[float]:
        bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
        min_x, min_y, max_x, max_y = bounds
        sx, sy = slot_pos

        # Determine nearest wall and face furniture away from wall (or parallel)
        d_left = abs(sx - min_x)
        d_right = abs(max_x - sx)
        d_bottom = abs(sy - min_y)
        d_top = abs(max_y - sy)
        min_d = min(d_left, d_right, d_bottom, d_top)

        if min_d == d_bottom:
            return [0.0, 180.0, 90.0, 270.0]
        elif min_d == d_top:
            return [180.0, 0.0, 270.0, 90.0]
        elif min_d == d_left:
            return [90.0, 270.0, 0.0, 180.0]
        else:
            return [270.0, 90.0, 180.0, 0.0]
