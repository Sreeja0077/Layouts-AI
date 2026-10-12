"""
Manager Cabin Near Rear Strategy Template (Task 9.1 - Strategy 4).
Prioritizes placing the manager cabin or executive desk in the rear private/executive zone,
maximizing privacy, quiet focus, and prestige positioning.
"""

import math
from typing import Any, Dict, List, Tuple
from geometry.geo_engine.strategies.base_strategy import StrategyTemplate


class ManagerCabinRearStrategy(StrategyTemplate):
    """Positions manager cabin/desk in the deep rear of the room, far from the entrance."""

    def __init__(self):
        super().__init__(
            strategy_id="CABIN_REAR",
            name="Manager Cabin Near Rear Strategy",
            description="Places the executive desk or manager cabin in the deep rear quiet zone, with team desks closer to the entrance.",
        )

    def get_anchoring_preference(self) -> str:
        return "CABIN_REAR"

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
            # Manager desk wants maximum distance from entrance (deepest rear zone)
            return max(0.0, 20.0 - dist_to_door)
        else:
            # Team workstations placed closer to entrance/middle
            return dist_to_door * 0.5

    def get_orientation_preferences(
        self,
        item_type: str,
        slot_pos: Tuple[float, float],
        context: Dict[str, Any],
    ) -> List[float]:
        # Manager in rear typically looks out toward the room entrance
        door_point = context.get("door_point")
        if not door_point:
            return [180.0, 0.0, 90.0, 270.0]

        dx, dy = door_point
        angle_rad = math.atan2(dy - slot_pos[1], dx - slot_pos[0])
        angle_deg = (math.degrees(angle_rad) + 360.0) % 360.0
        primary = round(angle_deg / 90.0) * 90.0 % 360.0
        return [primary, (primary + 180.0) % 360.0, (primary + 90.0) % 360.0, (primary + 270.0) % 360.0]
