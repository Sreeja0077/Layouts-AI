"""API v1 router definitions."""
from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.requirements import router as requirements_router
from app.api.v1.layout import router as layout_router
from app.api.v1.approvals import router as approvals_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(projects_router, prefix="/projects", tags=["Projects & Floor Plans"])
api_v1_router.include_router(requirements_router, prefix="/requirements", tags=["Requirements & Clarification"])
api_v1_router.include_router(layout_router, prefix="/layouts", tags=["Layout Generation & Iteration"])
api_v1_router.include_router(approvals_router, prefix="/approvals", tags=["Approvals & Audit"])
