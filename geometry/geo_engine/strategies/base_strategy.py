"""
Base Strategy Template Architecture for Layout Optimization (Task 9.1).
Defines abstract StrategyTemplate interface producing deterministic spatial hints,
preferred ordering, orientation preferences, grouping styles, and slot scoring.

CRITICAL INVARIANT: Strategy templates DO NOT directly invent final coordinates.
Exact world-metric coordinates are solved strictly by CP-SAT or heuristic geometry optimizers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class StrategyTemplate(ABC):
    """
    Abstract Layout Strategy Template.
    Produces deterministic optimization hints and heuristics for the solver engines.
    """

    def __init__(self, strategy_id: str, name: str, description: str):
        self.strategy_id = strategy_id
        self.name = name
        self.description = description

    @abstractmethod
    def get_anchoring_preference(self) -> str:
        """
        Return the primary geometric anchoring mode:
        'PERIMETER', 'TWO_ROW_CLUSTER', 'CABIN_ENTRANCE', 'CABIN_REAR', 'CIRCULATION_FOCUSED'.
        """
        pass

    def get_item_ordering(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Produce deterministic placement ordering for requested and movable items.
        Default: Fixed sold items first, then manager/executive items, then desks, then chairs.
        """
        def rank_item(it: Dict[str, Any]) -> Tuple[int, int]:
            movability = str(it.get("movability_status", "")).upper()
            item_type = str(it.get("item_type", "")).upper()

            # 0: SOLD_FIXED items (already placed/immutable)
            if movability == "SOLD_FIXED":
                return (0, 0)

            # 1: Manager/Executive items (anchor first)
            if "MANAGER" in item_type or "EXECUTIVE" in item_type or "CABIN" in item_type:
                return (1, 0)

            # 2: Desks / Workstations / Tables
            if "DESK" in item_type or "WORKSTATION" in item_type or "TABLE" in item_type:
                return (2, 0)

            # 3: Storage / Cabinets
            if "CABINET" in item_type or "STORAGE" in item_type:
                return (3, 0)

            # 4: Chairs / Soft seating
            if "CHAIR" in item_type or "SEAT" in item_type:
                return (4, 0)

            # 5: Other
            return (5, 0)

        return sorted(items, key=rank_item)

    def get_orientation_preferences(
        self,
        item_type: str,
        slot_pos: Tuple[float, float],
        context: Dict[str, Any],
    ) -> List[float]:
        """
        Return candidate orientation angles in degrees [0.0, 90.0, 180.0, 270.0],
        ordered by preference for this strategy.
        """
        return [0.0, 90.0, 180.0, 270.0]

    @abstractmethod
    def score_slot(
        self,
        slot_x: float,
        slot_y: float,
        item: Dict[str, Any],
        context: Dict[str, Any],
    ) -> float:
        """
        Calculate a deterministic score for placing 'item' at candidate slot (slot_x, slot_y).
        Lower score = higher preference in optimization ordering.
        """
        pass

    def get_optimization_hints(self) -> Dict[str, Any]:
        """Return solver parameter tuning hints (e.g. cluster spacing, aisle margin)."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "anchoring": self.get_anchoring_preference(),
            "min_aisle_width_m": 1.2,
            "cluster_spacing_m": 0.8,
        }
