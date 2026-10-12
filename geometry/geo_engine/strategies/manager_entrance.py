"""
Manager Cabin Near Entrance Strategy Template (Task 9.1 - Strategy 3).
Prioritizes placing the manager cabin or executive desk near the room entrance/access zone,
enabling direct visitor reception and quick exterior communication.
"""

import math
from typing import Any, Dict, List, Tuple
from geometry.geo_engine.strategies.base_strategy import StrategyTemplate


class ManagerCabinEntranceStrategy(StrategyTemplate):
    """Positions manager cabin/desk near the primary room entrance."""

    def __init__(self):
        super().__init__(
            strategy_id="CABIN_ENTRANCE",
            name="Manager Cabin Near Entrance Strategy",
            description="Places the executive desk or manager cabin near the primary entrance, with general desks positioned inward.",
        )

    def get_anchoring_preference(self) -> str:
        return "CABIN_ENTRANCE"

    def score_slot(
        self,
        slot_x: float,
        slot_y: float,
        item: Dict[str, Any],
        context: Dict[str, Any],
    ) -> float:
        door_point = context.get("door_point")
        if not door_point:
            bounds = context.get("bounds", (0.0, 0.0, 10.0, 10.0))
            door_point = ((bounds[0] + bounds[2]) / 2.0, bounds[1])

        dx, dy = door_point
        dist_to_door = math.hypot(slot_x - dx, slot_y - dy)

        item_type = str(item.get("item_type", "")).upper()
        is_manager = "MANAGER" in item_type or "EXECUTIVE" in item_type or "CABIN" in item_type

        if is_manager:
            # Manager desk wants to be close to entrance (but not directly blocking it, target ~1.5 - 2.5m)
            target_dist = 2.0
            return abs(dist_to_door - target_dist)
        else:
            # Other items prefer positions deeper into the room (higher distance from door = lower score)
            return max(0.0, 10.0 - dist_to_door)

    def get_orientation_preferences(
        self,
        item_type: str,
        slot_pos: Tuple[float, float],
        context: Dict[str, Any],
    ) -> List[float]:
        door_point = context.get("door_point")
        if not door_point:
            return [0.0, 180.0, 90.0, 270.0]

        # Orientation facing toward the door entrance
        dx, dy = door_point
        angle_rad = math.atan2(dy - slot_pos[1], dx - slot_pos[0])
        angle_deg = (math.degrees(angle_rad) + 360.0) % 360.0
        # Snap to nearest 90 deg
        primary = round(angle_deg / 90.0) * 90.0 % 360.0
        return [primary, (primary + 180.0) % 360.0, (primary + 90.0) % 360.0, (primary + 270.0) % 360.0]
