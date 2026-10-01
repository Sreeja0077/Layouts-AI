"""
Geometry Validity Rule (Task 4.2 - Rule 1).
Validates that all geometry supplied to the layout engine is valid (no self-intersections, zero-area, degenerate, or negative dimensions).
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class GeometryValidityRule(BaseRule):
    """Validates physical geometry parameters for placed objects and rooms."""

    def __init__(self):
        super().__init__(rule_id="geometry_validity", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []

        # Validate room geometry if provided
        if room and room.boundary_polygon:
            if len(room.boundary_polygon) < 3:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.OUT_OF_BOUNDS,
                        message=f"Room '{room.id}' boundary polygon has fewer than 3 vertices.",
                        affected_element_type="ROOM",
                    )
                )
            else:
                try:
                    poly = Polygon(room.boundary_polygon)
                    if not poly.is_valid:
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.OUT_OF_BOUNDS,
                                message=f"Room '{room.id}' boundary polygon is invalid or self-intersecting.",
                                affected_element_type="ROOM",
                            )
                        )
                    elif poly.area <= 0.0:
                        violations.append(
                            self.create_violation(
                                violation_type=ViolationType.OUT_OF_BOUNDS,
                                message=f"Room '{room.id}' boundary polygon has zero or negative area.",
                                affected_element_type="ROOM",
                            )
                        )
                except Exception as e:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.OUT_OF_BOUNDS,
                            message=f"Room '{room.id}' boundary polygon invalid: {str(e)}",
                            affected_element_type="ROOM",
                        )
                    )

        # Validate placed object footprints
        for obj in layout.placed_objects:
            if obj.width <= 0.0 or obj.height <= 0.0:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.COLLISION,
                        message=f"PlacedObject '{obj.id}' has invalid non-positive dimensions ({obj.width}x{obj.height}).",
                        affected_object_ids=[obj.id],
                    )
                )

        return violations
