"""
Projects and Floor Plans API router skeleton.
Handles project management, floor plan uploads, BIM geometry ingestion, human verification flows (Task 2.3),
and version publishing (Task 2.4).
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.bim.ifc_ingest import IFCIngestor
from app.bim.dxf_ingest import DXFIngestor
from app.bim.reconciliation import (
    GeometryReconciler,
    GeometryVerificationReport,
    VerificationStatus,
)
from app.domain.revisions import SourceVersionPublisher, FloorPlanSourceVersionPayload
from app.security.auth import AuthenticatedUser, UserRole, get_current_user

router = APIRouter()
publisher = SourceVersionPublisher()
reconciler = GeometryReconciler()

# In-memory store for verification reports (associated by floor_plan_id or file_name)
verification_reports_store: Dict[str, GeometryVerificationReport] = {}

ALLOWED_VERIFICATION_ROLES = {UserRole.LAYOUT_EXEC, UserRole.LAYOUT_MGR, UserRole.ADMIN}


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
async def ingest_and_verify_floor_plan(
    project_id: str,
    payload: Dict[str, Any],
) -> GeometryVerificationReport:
    """Ingest IFC or DXF file and return geometry verification report for Layouts Team review."""
    file_name = payload.get("file_name", "floor_plan.ifc")
    floor_plan_id = payload.get("floor_plan_id", "fp_501")

    # Resolve file path
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    if file_name.lower().endswith(".dxf"):
        dxf_path = root_dir / "docs" / "fixtures" / file_name if not Path(file_name).exists() else Path(file_name)
        if not dxf_path.exists():
            dxf_path = root_dir / "docs" / "fixtures" / "sample_floor_plan.dxf"
        dxf_ingestor = DXFIngestor()
        parsed_dxf = dxf_ingestor.parse_file(str(dxf_path))
        report = reconciler.reconcile_dxf(parsed_dxf)
    else:
        ifc_path = root_dir / "docs" / file_name if not Path(file_name).exists() else Path(file_name)
        if not ifc_path.exists():
            ifc_path = root_dir / "docs" / "4420 Ashland Rev 2.ifc"
        ifc_ingestor = IFCIngestor()
        parsed_ifc = ifc_ingestor.parse_file(str(ifc_path))
        report = reconciler.reconcile_ifc(parsed_ifc)

    verification_reports_store[floor_plan_id] = report
    verification_reports_store[file_name] = report
    return report


@router.get("/{project_id}/floor-plans/{floor_plan_id}/verification-report", response_model=GeometryVerificationReport)
async def get_verification_report(project_id: str, floor_plan_id: str) -> GeometryVerificationReport:
    """Get latest verification report and 2D rendering geometry for a floor plan."""
    if floor_plan_id in verification_reports_store:
        return verification_reports_store[floor_plan_id]
    
    # Auto-generate report on demand if not cached
    root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    ifc_path = root_dir / "docs" / "4420 Ashland Rev 2.ifc"
    parsed_ifc = IFCIngestor().parse_file(str(ifc_path))
    report = reconciler.reconcile_ifc(parsed_ifc)
    verification_reports_store[floor_plan_id] = report
    return report


@router.post("/{project_id}/floor-plans/{floor_plan_id}/verify", response_model=GeometryVerificationReport)
async def verify_floor_plan_geometry(
    project_id: str,
    floor_plan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GeometryVerificationReport:
    """
    Human verification endpoint for Layouts Team.
    Marks floor plan geometry as VERIFIED. Enforces RBAC permissions.
    """
    if current_user.role not in ALLOWED_VERIFICATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: User role '{current_user.role}' lacks Layouts Team verification permissions.",
        )

    report = verification_reports_store.get(floor_plan_id)
    if not report:
        # Fallback fetch
        report = await get_verification_report(project_id, floor_plan_id)

    if not report.is_geometry_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify floor plan geometry with critical errors or invalid structural boundaries.",
        )

    report.verification_status = VerificationStatus.VERIFIED
    report.reviewer_user_id = current_user.user_id
    report.verified_at = datetime.utcnow().isoformat()
    verification_reports_store[floor_plan_id] = report
    return report


@router.post("/{project_id}/floor-plans/{floor_plan_id}/reject", response_model=GeometryVerificationReport)
async def reject_floor_plan_geometry(
    project_id: str,
    floor_plan_id: str,
    payload: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GeometryVerificationReport:
    """
    Human rejection endpoint for Layouts Team.
    Marks floor plan geometry as REJECTED with mandatory rejection reason.
    """
    if current_user.role not in ALLOWED_VERIFICATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: User role '{current_user.role}' lacks Layouts Team verification permissions.",
        )

    reason = payload.get("rejection_reason", "").strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required when rejecting a floor plan.",
        )

    report = verification_reports_store.get(floor_plan_id)
    if not report:
        report = await get_verification_report(project_id, floor_plan_id)

    report.verification_status = VerificationStatus.REJECTED
    report.rejection_reason = reason
    report.reviewer_user_id = current_user.user_id
    report.verified_at = datetime.utcnow().isoformat()
    verification_reports_store[floor_plan_id] = report
    return report


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
