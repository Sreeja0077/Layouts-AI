"""
Circulation-Focused Strategy Template (Task 9.1 - Strategy 5).
Prioritizes maintaining wide, continuous, unobstructed central circulation aisles (>= 1.5m),
arranging furniture into lateral pods flanking the primary movement axis.
"""

import math
from typing import Any, Dict, List, Tuple
from geometry.geo_engine.strategies.base_strategy import StrategyTemplate


class CirculationFocusedStrategy(StrategyTemplate):
    """Preserves open central spine and primary egress corridors."""

    def __init__(self):
        super().__init__(
            strategy_id="CIRCULATION_FOCUSED",
            name="Circulation-Focused Strategy",
            description="Preserves an expansive central movement corridor, placing furniture in lateral zones to guarantee unblocked flow.",
        )

    def get_anchoring_preference(self) -> str:
        return "CIRCULATION_FOCUSED"

    def score_slot(
        self,
        slot_x: float,
        slot_y: float,
        item: Dict[str, Any],
        context: Dict[str, Any],
    ) -> float:
        bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
        min_x, min_y, max_x, max_y = bounds
        cx = (min_x + max_x) / 2.0

        # Penalize placing furniture directly on central axis (x = cx)
        # Reward placement in lateral zones (|x - cx| >= 1.2m)
        dist_from_central_axis = abs(slot_x - cx)
        if dist_from_central_axis < 0.9:
            # Inside primary circulation corridor
            return 50.0 + (0.9 - dist_from_central_axis) * 10.0

        # In lateral zone: prioritize compact clustering along Y
        return abs(dist_from_central_axis - 1.8) + abs(slot_y - min_y) * 0.3

    def get_orientation_preferences(
        self,
        item_type: str,
        slot_pos: Tuple[float, float],
        context: Dict[str, Any],
    ) -> List[float]:
        # Desks in lateral zones face toward or away from the central aisle
        bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
        cx = (bounds[0] + bounds[2]) / 2.0

        if slot_pos[0] < cx:
            # Left flank: face east (toward aisle) or north
            return [90.0, 0.0, 180.0, 270.0]
        else:
            # Right flank: face west (toward aisle) or north
            return [270.0, 0.0, 180.0, 90.0]

    def get_optimization_hints(self) -> Dict[str, Any]:
        hints = super().get_optimization_hints()
        hints["min_aisle_width_m"] = 1.5
        hints["corridor_clearance_m"] = 1.2
        return hints
