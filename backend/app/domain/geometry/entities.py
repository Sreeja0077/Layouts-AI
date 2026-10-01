"""
Canonical Floor Plan & Architectural BIM Entity Models.
Defines Shapely-compatible 2D spatial models for Wall, Door, Window, Column, Beam, Room, and FloorPlan entities.
"""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    WALL = "WALL"
    DOOR = "DOOR"
    WINDOW = "WINDOW"
    COLUMN = "COLUMN"
    BEAM = "BEAM"
    ROOM = "ROOM"
    EXISTING_FURNITURE = "EXISTING_FURNITURE"


class WallEntity(BaseModel):
    """Canonical 2D Wall entity (interior partition or exterior load-bearing wall)."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique wall entity ID or IFC GlobalId")
    start_point: Tuple[float, float] = Field(..., description="Start coordinate (x0, y0) in meters")
    end_point: Tuple[float, float] = Field(..., description="End coordinate (x1, y1) in meters")
    thickness_m: float = Field(default=0.15, gt=0.0, description="Wall thickness in meters (e.g. 0.15m drywall, 0.30m exterior)")
    is_exterior: bool = Field(default=False, description="True if load-bearing exterior perimeter wall")


class DoorEntity(BaseModel):
    """Canonical 2D Door entity with door swing arc polygon calculation."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique door entity ID or IFC GlobalId")
    wall_id: Optional[str] = Field(None, description="Host wall entity ID if attached")
    center_x: float = Field(..., description="Door center X coordinate in meters")
    center_y: float = Field(..., description="Door center Y coordinate in meters")
    width_m: float = Field(default=0.9, gt=0.0, description="Door opening width in meters (e.g. 0.9m / 1.2m)")
    swing_deg: float = Field(default=90.0, description="Door swing arc angle in degrees")
    swing_direction: str = Field(default="INSIDE_LEFT", description="INSIDE_LEFT, INSIDE_RIGHT, OUTSIDE_LEFT, OUTSIDE_RIGHT")

    def get_swing_arc_polygon(self, steps: int = 8) -> List[Tuple[float, float]]:
        """Calculate 2D door swing arc polygon vertices for exclusion checking."""
        radius = self.width_m
        cx, cy = self.center_x, self.center_y
        vertices: List[Tuple[float, float]] = [(cx, cy)]

        start_angle = 0.0
        end_angle = math.radians(self.swing_deg)
        angle_step = (end_angle - start_angle) / steps

        for i in range(steps + 1):
            angle = start_angle + (i * angle_step)
            vx = cx + radius * math.cos(angle)
            vy = cy + radius * math.sin(angle)
            vertices.append((round(vx, 3), round(vy, 3)))

        return vertices


class WindowEntity(BaseModel):
    """Canonical 2D Window entity providing natural lighting and placement preferences."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique window entity ID or IFC GlobalId")
    wall_id: Optional[str] = Field(None, description="Host wall entity ID")
    start_point: Tuple[float, float] = Field(..., description="Window start coordinate along wall")
    end_point: Tuple[float, float] = Field(..., description="Window end coordinate along wall")
    width_m: float = Field(..., gt=0.0, description="Window width in meters")
    sill_height_m: float = Field(default=0.9, ge=0.0, description="Window sill height above floor level")


class ColumnEntity(BaseModel):
    """Canonical 2D Structural Column entity (rectangular or circular pillar)."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique column entity ID or IFC GlobalId")
    center_x: float = Field(..., description="Column center X coordinate in meters")
    center_y: float = Field(..., description="Column center Y coordinate in meters")
    shape: str = Field(default="RECTANGULAR", description="RECTANGULAR or CIRCULAR")
    width_m: float = Field(default=0.6, gt=0.0, description="Width in meters")
    height_m: float = Field(default=0.6, gt=0.0, description="Depth/Height in meters")
    clearance_buffer_m: float = Field(default=0.2, ge=0.0, description="Safety clearance buffer around column")

    def get_obstacle_polygon(self) -> List[Tuple[float, float]]:
        """Get 2D bounding polygon including clearance buffer."""
        hw = (self.width_m / 2.0) + self.clearance_buffer_m
        hh = (self.height_m / 2.0) + self.clearance_buffer_m
        cx, cy = self.center_x, self.center_y
        return [
            (round(cx - hw, 3), round(cy - hh, 3)),
            (round(cx + hw, 3), round(cy - hh, 3)),
            (round(cx + hw, 3), round(cy + hh, 3)),
            (round(cx - hw, 3), round(cy + hh, 3)),
        ]


class BeamEntity(BaseModel):
    """Canonical 2D Overhead Structural Beam projection line."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique beam entity ID")
    start_point: Tuple[float, float] = Field(..., description="Start coordinate")
    end_point: Tuple[float, float] = Field(..., description="End coordinate")
    clearance_height_m: float = Field(default=2.4, gt=0.0, description="Bottom height of beam above floor level")


class RoomEntity(BaseModel):
    """Canonical 2D Room/Space entity containing boundary polygon and net area."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique room ID or IFC GlobalId")
    name: str = Field(..., description="Room name (e.g. 'Executive Office 401', 'Conference Room A')")
    boundary_polygon: List[Tuple[float, float]] = Field(..., description="Ordered 2D vertices [(x0, y0), (x1, y1)...]")
    net_area_sqm: float = Field(..., gt=0.0, description="Net usable floor area in square meters")

    wall_ids: List[str] = Field(default_factory=list)
    door_ids: List[str] = Field(default_factory=list)
    window_ids: List[str] = Field(default_factory=list)
    column_ids: List[str] = Field(default_factory=list)

    doors: List[DoorEntity] = Field(default_factory=list)
    windows: List[WindowEntity] = Field(default_factory=list)
    columns: List[ColumnEntity] = Field(default_factory=list)


class CanonicalFloorPlan(BaseModel):
    """Aggregated Canonical Floor Plan model holding all architectural BIM elements."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Floor plan ID")
    name: str = Field(..., description="Floor plan name")
    source_version_id: Optional[str] = Field(None, description="Published source version reference")

    rooms: List[RoomEntity] = Field(default_factory=list)
    walls: List[WallEntity] = Field(default_factory=list)
    doors: List[DoorEntity] = Field(default_factory=list)
    windows: List[WindowEntity] = Field(default_factory=list)
    columns: List[ColumnEntity] = Field(default_factory=list)
    beams: List[BeamEntity] = Field(default_factory=list)
