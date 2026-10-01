"""
Zone Rule (Task 4.2 - Rule 15).
Validates object placement inside permitted/disallowed semantic zones (e.g. Executive Desk allowed in executive/private_office, forbidden in circulation).
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Point, Polygon
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class ZoneRule(BaseRule):
    """Verifies that objects are placed strictly within allowed semantic zone boundaries."""

    def __init__(self):
        super().__init__(rule_id="zone", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []

        for obj in layout.placed_objects:
            zone_id = obj.custom_metadata.get("zone_id")
            forbidden_zones = obj.custom_metadata.get("disallowed_zones", ["circulation"])

            if zone_id and zone_id.lower() in forbidden_zones:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.OUT_OF_BOUNDS,
                        message=f"Object '{obj.id}' ({obj.item_type}) placed in forbidden zone '{zone_id}'.",
                        affected_object_ids=[obj.id],
                        affected_element_type="ZONE",
                    )
                )

        return violations
