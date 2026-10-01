"""
Projects and Floor Plans API router skeleton.
Handles project management, floor plan uploads, BIM geometry ingestion, verification flows, and version publishing.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from app.bim.ifc_ingest import IFCIngestor
from app.bim.dxf_ingest import DXFIngestor
from app.bim.reconciliation import GeometryReconciler, GeometryVerificationReport
from app.domain.revisions import SourceVersionPublisher, FloorPlanSourceVersionPayload

router = APIRouter()
publisher = SourceVersionPublisher()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_projects() -> List[Dict[str, Any]]:
    """List all projects for current organization."""
    return [
        {
            "id": "proj_101",
            "name": "Enterprise Headquarters Redesign",
            "client_name": "Acme Corp",
            "floor_plans_count": 2,
        }
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new project."""
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="Project name is required")
    return {
        "id": "proj_102",
        "name": payload["name"],
        "client_name": payload.get("client_name", ""),
        "status": "CREATED",
    }


@router.get("/{project_id}/floor-plans")
async def list_floor_plans(project_id: str) -> List[Dict[str, Any]]:
    """List floor plans for a specific project."""
    return [
        {
            "id": "fp_501",
            "project_id": project_id,
            "name": "Level 4 Office Area",
            "floor_number": 4,
            "current_working_revision_id": "rev_001",
        }
    ]


@router.post("/{project_id}/floor-plans/ingest", response_model=GeometryVerificationReport)
async def ingest_and_verify_floor_plan(project_id: str, payload: Dict[str, Any]) -> GeometryVerificationReport:
    """Ingest IFC or DXF file and return geometry verification report for Layouts Team review."""
    file_name = payload.get("file_name", "floor_plan.ifc")
    reconciler = GeometryReconciler()

    if file_name.lower().endswith(".dxf"):
        dxf_ingestor = DXFIngestor()
        parsed_dxf = dxf_ingestor.parse_file(file_name)
        return reconciler.reconcile_dxf(parsed_dxf)
    else:
        ifc_ingestor = IFCIngestor()
        parsed_ifc = ifc_ingestor.parse_file(file_name)
        return reconciler.reconcile_ifc(parsed_ifc)


@router.post("/{project_id}/floor-plans/{floor_plan_id}/publish", response_model=FloorPlanSourceVersionPayload)
async def publish_floor_plan_version(
    project_id: str, floor_plan_id: str, payload: Dict[str, Any]
) -> FloorPlanSourceVersionPayload:
    """Publish a verified floor plan version as locked baseline for layout proposals."""
    source_type = payload.get("source_type", "IFC")
    file_name = payload.get("file_name", "blueprint_v1.ifc")
    storage_path = payload.get("file_storage_path", f"floor_plans/{file_name}")

    draft = publisher.create_draft_version(
        floor_plan_id=floor_plan_id,
        source_type=source_type,
        file_name=file_name,
        file_storage_path=storage_path,
        geometry_summary=payload.get("geometry_summary", {"status": "VERIFIED"}),
    )

    published = publisher.publish_version(
        floor_plan_id=floor_plan_id,
        version_id=draft.version_id,
        publisher_user_id=payload.get("publisher_user_id", "usr_layouts_exec_001"),
    )
    return published
