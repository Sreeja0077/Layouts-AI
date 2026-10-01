"""
Layout domain schemas (Pydantic v2).
Defines LayoutSuggestion, PlacedObject, LayoutMetrics, and LayoutAction models for geometry proposals and AI iterative edits.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ActionType(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    MOVE = "MOVE"
    ROTATE = "ROTATE"
    SWAP = "SWAP"
    RENAME_ZONE = "RENAME_ZONE"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    RE_OPTIMIZE_REGION = "RE_OPTIMIZE_REGION"


class BoundingBox2D(BaseModel):
    """2D Bounding box representation (min_x, min_y, max_x, max_y)."""
    model_config = ConfigDict(extra="forbid")

    min_x: float
    min_y: float
    max_x: float
    max_y: float


class Polygon2D(BaseModel):
    """2D Polygon represented by ordered List of [x, y] coordinates."""
    model_config = ConfigDict(extra="forbid")

    vertices: List[Tuple[float, float]] = Field(
        ..., description="Outer ring coordinates [(x0, y0), (x1, y1), ...]"
    )


class PlacedObject(BaseModel):
    """A single placed furniture or fixture object in a 2D layout."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique instance ID of placed object")
    catalog_item_id: str = Field(..., description="ID in furniture catalog")
    item_type: str = Field(..., description="Category / type name (e.g. 'EXECUTIVE_DESK', 'WORKSTATION_POD')")

    x: float = Field(..., description="Center X coordinate in meters")
    y: float = Field(..., description="Center Y coordinate in meters")
    rotation_deg: float = Field(default=0.0, description="Rotation angle in degrees (0 - 360)")

    width: float = Field(..., gt=0.0, description="Bounding width in meters")
    height: float = Field(..., gt=0.0, description="Bounding height in meters")

    clearance_front: float = Field(default=0.8, ge=0.0, description="Front clearance buffer in meters")
    clearance_back: float = Field(default=0.5, ge=0.0, description="Rear clearance buffer in meters")
    clearance_sides: float = Field(default=0.2, ge=0.0, description="Side clearance buffer in meters")

    locked: bool = Field(default=False, description="Whether object is locked against re-optimization moves")
    tags: List[str] = Field(default_factory=list, description="Semantic tags (e.g. ['manager_cabin', 'locked_user'])")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional properties or attributes")


class CirculationPath(BaseModel):
    """An egress or aisle circulation line/corridor in the floor plan."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Circulation path segment identifier")
    path_type: str = Field(default="MAIN_AISLE", description="Path type: MAIN_AISLE, SECONDARY_AISLE, EGRESS_CORRIDOR")
    path_points: List[Tuple[float, float]] = Field(..., description="Line points defining circulation center line")
    min_width_meters: float = Field(default=1.2, gt=0.0, description="Minimum clearance width along corridor")


class LayoutMetrics(BaseModel):
    """Deterministic spatial metrics and scoring evaluation for a candidate layout."""
    model_config = ConfigDict(extra="forbid")

    total_seats: int = Field(default=0, ge=0, description="Total seat capacity achieved")
    used_floor_area_sqm: float = Field(default=0.0, ge=0.0, description="Total floor area occupied by furniture")
    circulation_area_sqm: float = Field(default=0.0, ge=0.0, description="Total area dedicated to circulation aisles")
    circulation_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Circulation area / total area ratio")

    power_reach_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Proximity to power/data core score")
    wall_utilization_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Wall alignment efficiency score")
    rule_compliance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Constraint & clearance compliance score (0-1)")

    composite_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall layout candidate score (0-100)")


class LayoutSuggestion(BaseModel):
    """A generated candidate layout proposal containing object coordinates & metrics."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique layout suggestion candidate ID")
    floor_plan_id: str = Field(..., description="Target floor plan ID")
    room_id: Optional[str] = Field(None, description="Optional target room ID")

    strategy_name: str = Field(..., description="Strategy name (e.g., 'Perimeter Cluster Strategy')")
    placed_objects: List[PlacedObject] = Field(default_factory=list, description="All placed furniture instances")
    circulation_paths: List[CirculationPath] = Field(default_factory=list, description="Circulation corridors")

    metrics: LayoutMetrics = Field(default_factory=LayoutMetrics, description="Calculated layout quality metrics")
    explanation: Optional[str] = Field(None, description="Natural language explanation of layout strategy & trade-offs")

    created_at: Optional[str] = Field(None, description="ISO timestamp")


class LayoutAction(BaseModel):
    """Semantic action instruction payload generated by ChangeInterpreter for iterative layout modification."""
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(..., description="Unique action ID")
    action_type: ActionType = Field(..., description="The type of action to perform")

    target_object_ids: List[str] = Field(default_factory=list, description="IDs of target objects if directly specified")
    target_phrase: Optional[str] = Field(None, description="Natural language reference phrase ('manager desk near window')")

    spatial_reference: Optional[str] = Field(None, description="Spatial reference location ('rear corner', 'left wall')")

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters (e.g. {'delta_x': 0.5, 'catalog_item_id': 'desk_120', 'rotation_deg': 90})"
    )

    scope_region_polygon: Optional[Polygon2D] = Field(
        None, description="Optional polygon bounding box for regional re-optimization"
    )
