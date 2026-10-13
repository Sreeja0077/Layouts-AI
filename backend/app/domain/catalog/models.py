"""
Furniture Catalog Domain Models (Phase 7 Task 7.1).
Defines authoritative typed Pydantic v2 schemas for furniture catalog items,
clearance requirements, footprint specifications, Revit source asset references,
and furniture bundle definitions.

CRITICAL INVARIANTS:
1. Physical definitions must be deterministic and verified. LLMs never define physical dimensions.
2. Dimensions clearly distinguish:
   - width_m (horizontal dimension along item's local X axis)
   - depth_m (horizontal dimension along item's local Y axis)
   - height_m (optional vertical 3D height along Z axis)
3. Zero ambiguous width/height representations.
4. Bundles reference catalog item IDs rather than duplicating physical furniture dimensions.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceAssetType(str, Enum):
    """Authoritative source asset formats."""
    REVIT_RFA = "REVIT_RFA"
    IFC_ELEMENT = "IFC_ELEMENT"
    PARAMETRIC_SPEC = "PARAMETRIC_SPEC"


class FurnitureCategory(str, Enum):
    """High-level architectural furniture categories."""
    DESK = "DESK"
    CHAIR = "CHAIR"
    CONFERENCE_TABLE = "CONFERENCE_TABLE"
    MEETING_TABLE = "MEETING_TABLE"
    STORAGE = "STORAGE"
    CABIN = "CABIN"
    DOOR = "DOOR"
    LOUNGE = "LOUNGE"
    ACCESSORY = "ACCESSORY"
    OTHER = "OTHER"


class ClearanceDefinition(BaseModel):
    """
    Clearance buffer requirements around furniture in meters.
    Defines required egress / access space per side.
    """
    model_config = ConfigDict(extra="ignore")

    front_m: float = Field(default=0.8, ge=0.0, description="Clearance in front of item (e.g. user seating/working space)")
    back_m: float = Field(default=0.2, ge=0.0, description="Clearance behind item (e.g. wall gap or rear access)")
    left_m: float = Field(default=0.2, ge=0.0, description="Clearance on left side")
    right_m: float = Field(default=0.2, ge=0.0, description="Clearance on right side")


class FootprintGeometry(BaseModel):
    """
    Deterministic 2D footprint definition for canvas rendering and spatial solver.
    Defaults to rectangular box (width_m x depth_m) centered or corner-aligned,
    or accepts explicit closed 2D polygon vertices in local item space (meters).
    """
    model_config = ConfigDict(extra="ignore")

    polygon_type: str = Field(default="RECTANGULAR", description="RECTANGULAR or CUSTOM_POLYGON")
    vertices: Optional[List[Tuple[float, float]]] = Field(
        default=None,
        description="Local 2D vertices [(x, y)] in meters relative to item origin (0, 0)."
    )


class FurnitureCatalogItem(BaseModel):
    """
    Authoritative typed domain representation of a verified furniture catalog item.
    Directly corresponds to verified physical assets from Revit RFA or architectural specs.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    catalog_item_id: str = Field(..., min_length=1, description="Stable unique catalog identifier")
    name: str = Field(..., min_length=1, description="User-facing display name")
    category: FurnitureCategory = Field(..., description="Primary architectural furniture category")
    subtype: Optional[str] = Field(default=None, description="Granular subtype (e.g. TASK_CHAIR, STANDING_DESK)")
    
    # Revit Specific Asset Metadata
    family_name: Optional[str] = Field(default=None, description="Authoritative Revit Family Name (.rfa)")
    family_type_name: Optional[str] = Field(default=None, description="Authoritative Revit Family Type Name")
    source_type: SourceAssetType = Field(default=SourceAssetType.REVIT_RFA, description="Origin format of asset")
    source_reference: Optional[str] = Field(
        default=None,
        description="Repository-relative or object-storage path to source asset (e.g. assets/catalog/revit/...)"
    )

    # Physical Dimensions (Explicit separation of width, depth, height)
    width_m: float = Field(..., gt=0.0, description="Width along item X axis in meters (must be > 0)")
    depth_m: float = Field(..., gt=0.0, description="Depth along item Y axis in meters (must be > 0)")
    height_m: Optional[float] = Field(default=None, gt=0.0, description="Optional 3D vertical height in meters")

    # Spatial definitions
    footprint_geometry: Optional[FootprintGeometry] = Field(
        default=None,
        description="2D footprint representation. If omitted, a width_m x depth_m rectangle is used."
    )
    clearance: ClearanceDefinition = Field(
        default_factory=ClearanceDefinition,
        description="Clearance buffer required for egress/usability"
    )

    # State & Verification
    is_active: bool = Field(default=True, description="Whether item is enabled for layouts and catalog selection")
    is_verified: bool = Field(default=True, description="Whether physical dimensions have been verified against real asset")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary verified manufacturer or Revit properties")

    @field_validator("width_m", "depth_m")
    @classmethod
    def validate_positive_dimensions(cls, v: float, info) -> float:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be strictly positive (> 0.0 meters).")
        return round(float(v), 4)


class BundleComponentPlacement(BaseModel):
    """
    A single component item positioned within a furniture bundle.
    References an authoritative catalog_item_id with relative placement.
    """
    model_config = ConfigDict(extra="ignore")

    component_id: str = Field(..., description="Unique component key within the bundle (e.g. desk_main, chair_1)")
    catalog_item_id: str = Field(..., description="Foreign key to authoritative FurnitureCatalogItem.catalog_item_id")
    quantity: int = Field(default=1, ge=1, description="Quantity of this component in the bundle")
    relative_x_m: float = Field(default=0.0, description="Local relative X coordinate from bundle origin (meters)")
    relative_y_m: float = Field(default=0.0, description="Local relative Y coordinate from bundle origin (meters)")
    relative_rotation_deg: float = Field(default=0.0, description="Local rotation relative to bundle orientation (degrees)")
    is_primary: bool = Field(default=False, description="Whether this is the primary anchor component of the bundle")


class FurnitureBundle(BaseModel):
    """
    Authoritative definition of a composite furniture bundle (e.g. EXECUTIVE_DESK_BUNDLE).
    Composed of multiple catalog items arranged according to architectural standards.
    """
    model_config = ConfigDict(extra="ignore")

    bundle_id: str = Field(..., min_length=1, description="Stable unique bundle identifier (e.g. EXECUTIVE_DESK_BUNDLE)")
    name: str = Field(..., min_length=1, description="User-facing display name")
    category: FurnitureCategory = Field(..., description="Primary category of the composite bundle")
    description: Optional[str] = Field(default=None, description="Architectural description of the bundle arrangement")
    
    components: List[BundleComponentPlacement] = Field(
        ...,
        min_length=1,
        description="Ordered list of catalog components with relative placement"
    )
    
    default_arrangement: str = Field(default="STANDARD", description="Arrangement rule / layout pattern name")
    orientation_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rules governing bundle placement (e.g. primary orientation toward window or entrance)"
    )
    clearance_requirements: Optional[ClearanceDefinition] = Field(
        default=None,
        description="Overall bundle outer perimeter clearance requirement"
    )
    
    is_active: bool = Field(default=True, description="Whether bundle is active for selection")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional domain metadata")

    @field_validator("components")
    @classmethod
    def validate_components_non_empty(cls, comps: List[BundleComponentPlacement]) -> List[BundleComponentPlacement]:
        if not comps:
            raise ValueError("A FurnitureBundle must contain at least one component.")
        return comps
