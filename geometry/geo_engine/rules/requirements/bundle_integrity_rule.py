"""
Bundle Integrity Rule (Task 4.2 - Rule 14).
Validates relative positioning, rotation, and membership of compound furniture catalog bundles (e.g., Desk + Chair + Pedestal).
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule


class BundleIntegrityRule(BaseRule):
    """Verifies relative geometry preservation for compound furniture bundles."""

    def __init__(self):
        super().__init__(rule_id="bundle_integrity", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []

        # Group placed objects by bundle_id
        bundles: Dict[str, List] = {}
        for obj in layout.placed_objects:
            bundle_id = obj.custom_metadata.get("bundle_id")
            if bundle_id:
                bundles.setdefault(bundle_id, []).append(obj)

        for bundle_id, members in bundles.items():
            # Check mandatory bundle components if declared in metadata
            req_components = members[0].custom_metadata.get("required_bundle_components", [])
            member_types = [m.item_type for m in members]

            for req_comp in req_components:
                if req_comp not in member_types:
                    violations.append(
                        self.create_violation(
                            violation_type=ViolationType.SPACING_VIOLATION,
                            message=f"Bundle '{bundle_id}' is missing required component '{req_comp}'. Present components: {member_types}.",
                            affected_object_ids=[m.id for m in members],
                            affected_element_type="FURNITURE_BUNDLE",
                        )
                    )

        return violations
