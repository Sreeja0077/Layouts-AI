"""
Default Rule Configuration for Layout Validation Rules Engine.
Defines project and company default thresholds for circulation, accessibility, furniture clearances,
storage wall gaps, and fulfillment modes.
"""

from typing import Any, Dict

DEFAULT_RULESET_CONFIG: Dict[str, Any] = {
    "circulation": {
        "main_aisle_min_mm": 1200,      # 1.2 meters
        "secondary_aisle_min_mm": 900,  # 0.9 meters
        "local_aisle_min_mm": 750,      # 0.75 meters
    },
    "accessibility": {
        "accessible_route_min_mm": 900, # 0.9 meters
        "turning_diameter_mm": 1500,    # 1.5 meters
        "accessible_approach_mm": 900,
    },
    "furniture": {
        "chair_clearance_mm": 800,        # 0.8 meters space behind chair
        "workstation_clearance_mm": 900,  # 0.9 meters workspace buffer
        "cabinet_front_clearance_mm": 900,# 0.9 meters front of storage
        "min_wall_gap_mm": 50,            # 50mm storage gap
    },
    "storage": {
        "min_wall_gap_mm": 50,
    },
    "quantity": {
        "partial_fulfillment": {
            "mode": "warning",  # Options: "reject", "warning", "allow"
        }
    },
    "doors": {
        "entrance_approach_clearance_mm": 1000, # 1.0 meter entrance approach
    },
    "windows": {
        "natural_light_max_distance_mm": 6000,   # 6.0 meters
        "tall_object_height_threshold_mm": 1400, # 1.4 meters
    }
}


def get_ruleset_config(custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Merge custom configuration overrides into default ruleset config."""
    if not custom_config:
        return DEFAULT_RULESET_CONFIG.copy()

    merged = DEFAULT_RULESET_CONFIG.copy()
    for category, settings in custom_config.items():
        if category in merged and isinstance(settings, dict):
            merged[category] = {**merged[category], **settings}
        else:
            merged[category] = settings
    return merged
