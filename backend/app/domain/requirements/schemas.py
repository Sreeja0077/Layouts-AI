"""
RequirementSet domain schemas (Pydantic v2).
Defines requirements extracted from user text/voice input for floor plan layout generation.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RequirementStatus(str, Enum):
    DRAFT = "DRAFT"
    NORMALIZED = "NORMALIZED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    FINALIZED = "FINALIZED"


class ResolutionMethod(str, Enum):
    EXACT_ALIAS = "EXACT_ALIAS"
    EMBEDDING_SIMILARITY = "EMBEDDING_SIMILARITY"
    MANUAL_CLARIFICATION = "MANUAL_CLARIFICATION"
    DEFAULT_FALLBACK = "DEFAULT_FALLBACK"


class RequirementItem(BaseModel):
    """A single requested furniture or space element in a requirement set."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for this requirement item entry")
    raw_phrase: str = Field(..., description="Raw phrase parsed from user input (e.g., '6 executive desks')")
    resolved_catalog_item_id: Optional[str] = Field(
        None, description="Catalog item ID resolved after catalog/alias lookup"
    )
    resolution_method: Optional[ResolutionMethod] = Field(
        None, description="Method used to resolve catalog item ID"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Resolution confidence score (0.0 - 1.0)"
    )
    quantity: int = Field(default=1, ge=1, description="Quantity requested")
    slot_tags: List[str] = Field(
        default_factory=list,
        description="Slot or zone tags (e.g. ['manager_cabin', 'window_side'])"
    )
    dimensions_override: Optional[Dict[str, float]] = Field(
        None, description="Optional custom width/height override in meters {'width': 1.4, 'height': 0.8}"
    )


class SpatialPreference(BaseModel):
    """Zone or proximity preference constraints specified by user."""
    model_config = ConfigDict(extra="forbid")

    target_zone: str = Field(..., description="Target area or zone name (e.g. 'rear_left', 'entrance', 'perimeter')")
    item_ids_or_tags: List[str] = Field(..., description="Requirement item IDs or slot tags affected")
    preference_type: str = Field(
        ..., description="Type of preference (e.g. 'NEAR_WINDOW', 'NEAR_ENTRANCE', 'FAR_FROM_NOISE', 'CLUSTER')"
    )
    importance: str = Field(default="MEDIUM", description="Importance level: HIGH, MEDIUM, LOW")


class RequirementSet(BaseModel):
    """Complete requirement specification set for a floor plan layout task."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique requirement set identifier")
    project_id: str = Field(..., description="Associated project ID")
    floor_plan_id: str = Field(..., description="Associated target floor plan ID")
    room_id: Optional[str] = Field(None, description="Optional specific target room/region ID")

    status: RequirementStatus = Field(
        default=RequirementStatus.DRAFT, description="Current requirement processing state"
    )

    items: List[RequirementItem] = Field(
        default_factory=list, description="Parsed requirement item entries"
    )
    preferences: List[SpatialPreference] = Field(
        default_factory=list, description="Spatial and proximity preferences"
    )

    target_density_seats: Optional[int] = Field(
        None, ge=1, description="Target total seat capacity requested by user"
    )
    target_circulation_ratio: float = Field(
        default=0.30, ge=0.10, le=0.60, description="Target aisle/circulation ratio (default 30%)"
    )

    notes: Optional[str] = Field(None, description="Additional user notes or transcript summary")
    created_at: Optional[str] = Field(None, description="ISO timestamp of creation")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last update")
