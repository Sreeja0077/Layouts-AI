"""
Aisle Width Rule (Task 4.2 - Rule 6).
Validates main and secondary circulation corridors ensuring path width and geometry meet configurable ruleset thresholds.
"""

from typing import Any, Dict, List, Optional
from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ViolationSeverity, ViolationType
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config


class AisleWidthRule(BaseRule):
    """Verifies that circulation corridors meet minimum configured width standards."""

    def __init__(self):
        super().__init__(rule_id="aisle_width", severity=ViolationSeverity.CRITICAL_HARD)

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
        config: Dict[str, Any] = None,
    ) -> List[ConstraintViolation]:
        violations = []
        cfg = get_ruleset_config(config)
        circ_cfg = cfg.get("circulation", {})

        main_min_m = circ_cfg.get("main_aisle_min_mm", 1200) / 1000.0
        sec_min_m = circ_cfg.get("secondary_aisle_min_mm", 900) / 1000.0

        for path in layout.circulation_paths:
            if not path.path_points or len(path.path_points) < 2:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message=f"Circulation corridor '{path.id}' has invalid or insufficient path points.",
                        affected_element_type="CIRCULATION_PATH",
                    )
                )
                continue

            if path.min_width_meters <= 0.0:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message=f"Circulation corridor '{path.id}' has non-positive width ({path.min_width_meters}m).",
                        affected_element_type="CIRCULATION_PATH",
                    )
                )
                continue

            required_m = main_min_m if path.path_type.upper() == "MAIN_AISLE" else sec_min_m
            if path.min_width_meters < required_m:
                violations.append(
                    self.create_violation(
                        violation_type=ViolationType.EGRESS_BLOCKAGE,
                        message=f"Circulation corridor '{path.id}' ({path.path_type}) width {path.min_width_meters:.2f}m is below required minimum of {required_m:.2f}m.",
                        affected_element_type="CIRCULATION_PATH",
                    )
                )

        return violations
