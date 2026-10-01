"""
Floor Plan Source Versioning and Publishing Engine.
Manages FloorPlanSourceVersion publishing, version number incrementing, and locked baseline snapshot points.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FloorPlanSourceVersionPayload(BaseModel):
    """Payload representing a published floor plan source version baseline."""
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(..., description="Unique source version ID")
    floor_plan_id: str = Field(..., description="Associated floor plan ID")
    version_no: int = Field(..., ge=1, description="Sequential version number (1, 2, 3...)")
    source_type: str = Field(..., description="Source format ('IFC', 'DXF', 'PDF', 'RASTER_IMAGE')")
    file_name: str = Field(..., description="Original uploaded file name")
    file_storage_path: str = Field(..., description="Storage key reference in Object Storage")
    is_published: bool = Field(default=False, description="True if locked as published baseline")
    published_by_user_id: Optional[str] = Field(None, description="User ID of publisher")
    published_at: Optional[str] = Field(None, description="ISO timestamp of publishing")
    geometry_summary: Dict[str, Any] = Field(default_factory=dict, description="Verified room counts & boundaries")


class SourceVersionPublisher:
    """Engine managing floor plan source versioning and publishing transitions."""

    def __init__(self):
        self._versions_db: Dict[str, List[FloorPlanSourceVersionPayload]] = {}

    def create_draft_version(
        self,
        floor_plan_id: str,
        source_type: str,
        file_name: str,
        file_storage_path: str,
        geometry_summary: Dict[str, Any],
    ) -> FloorPlanSourceVersionPayload:
        """Create a new draft source version for a floor plan."""
        existing = self._versions_db.get(floor_plan_id, [])
        next_version_no = len(existing) + 1

        version = FloorPlanSourceVersionPayload(
            version_id=f"ver_fp_{floor_plan_id}_{next_version_no}",
            floor_plan_id=floor_plan_id,
            version_no=next_version_no,
            source_type=source_type,
            file_name=file_name,
            file_storage_path=file_storage_path,
            is_published=False,
            geometry_summary=geometry_summary,
        )

        existing.append(version)
        self._versions_db[floor_plan_id] = existing
        return version

    def publish_version(
        self, floor_plan_id: str, version_id: str, publisher_user_id: str
    ) -> FloorPlanSourceVersionPayload:
        """Publish a specific floor plan source version as locked baseline."""
        versions = self._versions_db.get(floor_plan_id, [])
        target_ver = None

        for ver in versions:
            if ver.version_id == version_id:
                ver.is_published = True
                ver.published_by_user_id = publisher_user_id
                ver.published_at = datetime.utcnow().isoformat()
                target_ver = ver
                break

        if target_ver is None:
            raise ValueError(f"Version ID '{version_id}' not found for floor plan '{floor_plan_id}'")

        return target_ver

    def get_source_versions(self, floor_plan_id: str) -> List[FloorPlanSourceVersionPayload]:
        """List all source versions for a floor plan."""
        return self._versions_db.get(floor_plan_id, [])
