"""
Base Rule Interface for Layout Validation Engine (Task 4.2).
All 20 deterministic rules inherit from BaseRule and return structured ConstraintViolation objects.
Enforces deterministic violation IDs derived via SHA-256 hash.
"""

from abc import ABC, abstractmethod
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet


class BaseRule(ABC):
    """Abstract base class for all deterministic layout validation rules."""

    def __init__(self, rule_id: str, severity: ViolationSeverity):
        self.rule_id = rule_id
        self.severity = severity

    @abstractmethod
    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        """
        Evaluate layout against this rule (Read-only, zero side effects).

        Returns:
            List of ConstraintViolation objects (empty list if rule passes).
        """
        pass

    def create_violation(
        self,
        violation_type: ViolationType,
        message: str,
        affected_object_ids: Optional[List[str]] = None,
        affected_element_type: Optional[str] = None,
        penalty_score: float = 0.0,
        overlap_polygon_coords: Optional[List[Tuple[float, float]]] = None,
        violation_key: Optional[str] = None,
        severity: Optional[ViolationSeverity] = None,
    ) -> ConstraintViolation:
        """
        Helper constructing a deterministic ConstraintViolation object.
        Violation IDs are derived deterministically using a SHA-256 hash of rule parameters.
        """
        eff_severity = severity if severity is not None else self.severity
        sorted_objs = ",".join(sorted(affected_object_ids or []))
        v_key = violation_key or message[:40]
        id_seed = f"{self.rule_id}|{violation_type.value}|{eff_severity.value}|{sorted_objs}|{affected_element_type or ''}|{v_key}"
        deterministic_id = f"{self.rule_id}_{sha256(id_seed.encode('utf-8')).hexdigest()[:12]}"

        eff_penalty = penalty_score if eff_severity == ViolationSeverity.WARNING_SOFT else 0.0
        if eff_severity == ViolationSeverity.WARNING_SOFT and eff_penalty <= 0.0:
            eff_penalty = 0.2

        return ConstraintViolation(
            id=deterministic_id,
            violation_type=violation_type,
            severity=eff_severity,
            affected_object_ids=affected_object_ids or [],
            affected_element_type=affected_element_type,
            message=message,
            penalty_score=eff_penalty,
            overlap_polygon_coords=overlap_polygon_coords,
        )

    @staticmethod
    def extract_overlap_coords(inter: Any, decimals: int = 4) -> Optional[List[Tuple[float, float]]]:
        """Safely extract 2D polygon vertices from a Shapely intersection result without crashing on non-polygons."""
        if inter is None or inter.is_empty:
            return None
        try:
            if inter.geom_type == "Polygon":
                return [(round(p[0], decimals), round(p[1], decimals)) for p in inter.exterior.coords]
            elif inter.geom_type == "MultiPolygon":
                coords = []
                for poly in inter.geoms:
                    coords.extend([(round(p[0], decimals), round(p[1], decimals)) for p in poly.exterior.coords])
                return coords
        except Exception:
            pass
        return None
