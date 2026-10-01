"""
Rules Engine Package.
Provides deterministic architectural placement validation rules and central RuleEvaluator.
"""

from geometry.geo_engine.rules.base_rule import BaseRule
from geometry.geo_engine.rules.config import DEFAULT_RULESET_CONFIG, get_ruleset_config
from geometry.geo_engine.rules.rule_evaluator import RuleEvaluator

__all__ = [
    "BaseRule",
    "RuleEvaluator",
    "DEFAULT_RULESET_CONFIG",
    "get_ruleset_config",
]
