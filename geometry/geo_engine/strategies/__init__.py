"""
Layout Strategy Templates Package (Task 9.1).
Exports reusable layout strategy generators for deterministic spatial optimization.
"""

from typing import Dict, List, Optional
from geometry.geo_engine.strategies.base_strategy import StrategyTemplate
from geometry.geo_engine.strategies.perimeter import PerimeterStrategy
from geometry.geo_engine.strategies.two_row_clusters import TwoRowClusterStrategy
from geometry.geo_engine.strategies.manager_entrance import ManagerCabinEntranceStrategy
from geometry.geo_engine.strategies.manager_rear import ManagerCabinRearStrategy
from geometry.geo_engine.strategies.circulation_focused import CirculationFocusedStrategy

ALL_STRATEGIES: List[StrategyTemplate] = [
    PerimeterStrategy(),
    TwoRowClusterStrategy(),
    ManagerCabinEntranceStrategy(),
    ManagerCabinRearStrategy(),
    CirculationFocusedStrategy(),
]

_STRATEGY_MAP: Dict[str, StrategyTemplate] = {
    s.strategy_id.upper(): s for s in ALL_STRATEGIES
}


def get_all_strategies() -> List[StrategyTemplate]:
    """Return all available layout strategy templates."""
    return list(ALL_STRATEGIES)


def get_strategy(strategy_id: str) -> Optional[StrategyTemplate]:
    """Lookup a strategy template by ID."""
    return _STRATEGY_MAP.get(strategy_id.upper())
