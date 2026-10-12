"""
Two-Row Clusters Strategy Template (Task 9.1 - Strategy 2).
Prioritizes grouping workstations and desks into back-to-back dual-row pods,
optimizing cabling core runs and team collaboration density.
"""

import math
from typing import Any, Dict, List, Tuple
from geometry.geo_engine.strategies.base_strategy import StrategyTemplate


class TwoRowClusterStrategy(StrategyTemplate):
    """Groups workstations into back-to-back facing rows or cluster pods."""

    def __init__(self):
        super().__init__(
            strategy_id="TWO_ROW_CLUSTERS",
            name="Two-Row Clusters Strategy",
            description="Arranges workstations into back-to-back dual-row clusters, optimizing density and cable channels.",
        )

    def get_anchoring_preference(self) -> str:
        return "TWO_ROW_CLUSTER"

    def score_slot(
        self,
        slot_x: float,
        slot_y: float,
        item: Dict[str, Any],
        context: Dict[str, Any],
    ) -> float:
        bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
        min_x, min_y, max_x, max_y = bounds
        cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0

        item_type = str(item.get("item_type", "")).upper()
        is_manager = "MANAGER" in item_type or "EXECUTIVE" in item_type or "CABIN" in item_type

        if is_manager:
            # Place manager at the perimeter end of the room
            return abs(slot_y - max_y) + abs(slot_x - cx) * 0.5

        # Workstations: cluster in paired rows around center lines
        # Prefer alignment with row lanes (e.g. step intervals along X or Y)
        row_lane_offset = abs(slot_x - cx) % 1.6
        dist_from_core = math.hypot(slot_x - cx, slot_y - cy)
        return row_lane_offset * 2.0 + dist_from_core * 0.4

    def get_orientation_preferences(
        self,
        item_type: str,
        slot_pos: Tuple[float, float],
        context: Dict[str, Any],
    ) -> List[float]:
        # Back-to-back pods typically face 0 or 180 degrees (North/South)
        bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
        cy = (bounds[1] + bounds[3]) / 2.0

        if slot_pos[1] >= cy:
            return [180.0, 0.0, 90.0, 270.0]
        else:
            return [0.0, 180.0, 270.0, 90.0]
