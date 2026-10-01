"""
Rule Evaluator Central Engine (Task 4.2).
Aggregates and executes 16 HARD rules and 4 SOFT rules, returning a comprehensive ValidationResult.
"""

import time
from typing import Any, Dict, List, Optional

from app.domain.geometry.entities import RoomEntity
from app.domain.geometry.schemas import ConstraintViolation, ValidationResult, ViolationSeverity
from app.domain.layout.schemas import LayoutSuggestion
from app.domain.requirements.schemas import RequirementSet
from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import get_ruleset_config

# 16 HARD RULES
from geometry.geo_engine.rules.geometry import (
    GeometryValidityRule,
    CollisionRule,
    ContainmentRule,
    FixedObjectIntegrityRule,
)
from geometry.geo_engine.rules.circulation import (
    ClearanceRule,
    AisleWidthRule,
    AccessibilityRule,
    EgressRule,
    DoorSwingRule,
    EntranceObstructionRule,
)
from geometry.geo_engine.rules.requirements import (
    RequirementComplianceRule,
    QuantityFulfillmentRule,
    CapacityRule,
    BundleIntegrityRule,
)
from geometry.geo_engine.rules.spatial import ZoneRule, ConnectivityRule

# 4 SOFT RULES
from geometry.geo_engine.rules.spatial import OrientationRule
from geometry.geo_engine.rules.design import (
    WindowObstructionRule,
    WallProximityRule,
    NaturalLightRule,
)


class RuleEvaluator:
    """Central deterministic validation engine evaluating layout proposals against 20 architectural rules."""

    def __init__(self, custom_ruleset_config: Optional[Dict[str, Any]] = None):
        self.config = get_ruleset_config(custom_ruleset_config)

        self.hard_rules: List[BaseRule] = [
            GeometryValidityRule(),
            CollisionRule(),
            ContainmentRule(),
            FixedObjectIntegrityRule(),
            ClearanceRule(),
            AisleWidthRule(),
            AccessibilityRule(),
            EgressRule(),
            DoorSwingRule(),
            EntranceObstructionRule(),
            RequirementComplianceRule(),
            QuantityFulfillmentRule(),
            CapacityRule(),
            BundleIntegrityRule(),
            ZoneRule(),
            ConnectivityRule(),
        ]

        self.soft_rules: List[BaseRule] = [
            OrientationRule(),
            WindowObstructionRule(),
            WallProximityRule(),
            NaturalLightRule(),
        ]

    def evaluate(
        self,
        layout: LayoutSuggestion,
        room: Optional[RoomEntity] = None,
        requirements: Optional[RequirementSet] = None,
    ) -> ValidationResult:
        """
        Execute full validation suite against a candidate layout.

        Args:
            layout: LayoutSuggestion candidate containing placed objects & paths.
            room: Optional target RoomEntity containing boundaries, doors, windows, and columns.
            requirements: Optional RequirementSet containing user headcount and target space items.

        Returns:
            ValidationResult containing is_valid status, hard_violations list, soft_violations list, and compliance score.
        """
        start_time = time.perf_counter()

        hard_violations: List[ConstraintViolation] = []
        soft_violations: List[ConstraintViolation] = []

        # 1. Run all 16 Hard Rules
        for rule in self.hard_rules:
            try:
                results = rule.evaluate(layout=layout, room=room, requirements=requirements, config=self.config)
                hard_violations.extend(results)
            except Exception as e:
                # Catch unexpected exception as a hard violation
                hard_violations.append(
                    rule.create_violation(
                        violation_type=rule.hard_rules[0].severity,
                        message=f"Rule '{rule.rule_id}' raised runtime exception: {str(e)}",
                    )
                )

        # 2. Run all 4 Soft Rules
        for rule in self.soft_rules:
            try:
                results = rule.evaluate(layout=layout, room=room, requirements=requirements, config=self.config)
                soft_violations.extend(results)
            except Exception as e:
                pass

        execution_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

        # Layout is valid if 0 hard violations exist
        is_valid = len(hard_violations) == 0
        total_count = len(hard_violations) + len(soft_violations)

        # Calculate normalized compliance score (deduct soft penalties)
        total_soft_penalty = sum(v.penalty_score for v in soft_violations)
        compliance_score = max(0.0, min(1.0, 1.0 - (total_soft_penalty / 100.0)))
        if not is_valid:
            compliance_score = round(compliance_score * 0.5, 3)

        return ValidationResult(
            is_valid=is_valid,
            total_violations_count=total_count,
            hard_violations=hard_violations,
            soft_violations=soft_violations,
            overall_rule_compliance_score=round(compliance_score, 3),
            rule_execution_time_ms=execution_ms,
        )
