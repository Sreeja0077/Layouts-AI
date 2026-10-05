"""
Geometry validation domain schemas (Pydantic v2).
Defines ValidationResult and ConstraintViolation models returned by deterministic rule engines.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ViolationSeverity(str, Enum):
    CRITICAL_HARD = "CRITICAL_HARD"  # Must be fixed, invalid layout
    WARNING_SOFT = "WARNING_SOFT"   # Sub-optimal, valid layout with penalty


class ViolationType(str, Enum):
    COLLISION = "COLLISION"                         # Object geometries overlap
    CLEARANCE_OVERLAP = "CLEARANCE_OVERLAP"         # Required clearance zones overlap inappropriately
    DOOR_SWING_OBSTRUCTION = "DOOR_SWING_OBSTRUCTION" # Furniture blocks door arc
    WINDOW_OBSTRUCTION = "WINDOW_OBSTRUCTION"       # Tall object blocks window
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"                 # Object extends outside room boundary
    EGRESS_BLOCKAGE = "EGRESS_BLOCKAGE"             # Egress path width below minimum requirement
    COLUMN_COLLISION = "COLUMN_COLLISION"           # Object collides with structural column
    SPACING_VIOLATION = "SPACING_VIOLATION"         # Violates minimum inter-desk spacing
    RULE_EXECUTION_ERROR = "RULE_EXECUTION_ERROR"   # Runtime exception raised during rule execution



class ConstraintViolation(BaseModel):
    """Details of a single constraint rule violation."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique violation ID")
    violation_type: ViolationType = Field(..., description="Category of rule violation")
    severity: ViolationSeverity = Field(..., description="Severity level of violation")

    affected_object_ids: List[str] = Field(
        default_factory=list, description="IDs of layout objects involved in violation"
    )
    affected_element_type: Optional[str] = Field(
        None, description="Structural element involved (e.g., 'DOOR', 'WALL', 'COLUMN', 'WINDOW')"
    )

    message: str = Field(..., description="Human-readable explanation of violation")
    penalty_score: float = Field(default=0.0, ge=0.0, description="Penalty deducted from compliance score")

    overlap_polygon_coords: Optional[List[Tuple[float, float]]] = Field(
        None, description="Optional 2D polygon vertices of the collision/violation area"
    )


class ValidationResult(BaseModel):
    """Complete validation result returned after inspecting layout geometry against hard/soft rules."""
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if 0 CRITICAL_HARD violations exist")
    total_violations_count: int = Field(default=0, ge=0, description="Total number of violations")

    hard_violations: List[ConstraintViolation] = Field(
        default_factory=list, description="List of hard rule violations blocking approval"
    )
    soft_violations: List[ConstraintViolation] = Field(
        default_factory=list, description="List of soft rule warnings"
    )

    overall_rule_compliance_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Normalized compliance score (1.0 = perfect, 0.0 = total failure)"
    )

    rule_execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Time taken by geometry engine to run all checks (ms)"
    )
