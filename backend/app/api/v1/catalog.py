"""
Furniture Catalog & Bundles API Router (Phase 7 Task 7.1).
Exposes authoritative verified furniture catalog items, footprint metadata,
composite bundles, and RFA discovery audit records.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.domain.catalog.catalog_service import CatalogService
from app.domain.catalog.manifest import scan_revit_assets, AssetDiscoveryReport
from app.domain.catalog.models import (
    FurnitureBundle,
    FurnitureCatalogItem,
)
from app.domain.catalog.seeder import seed_catalog
from app.persistence.database import get_db

router = APIRouter()


@router.get("/furniture", response_model=List[Dict[str, Any]])
def list_furniture_catalog(
    category: Optional[str] = Query(None, description="Filter by category (e.g. DESK, CHAIR, STORAGE)"),
    include_inactive: bool = Query(False, description="Whether to include inactive items"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    List authoritative verified furniture catalog items.
    Reads directly from PostgreSQL database.
    """
    # Seed catalog automatically if database has 0 items
    items = CatalogService.list_catalog_items(db, category=category, only_active=not include_inactive)
    if not items:
        # Check if seeder needs to run
        seed_catalog(db)
        items = CatalogService.list_catalog_items(db, category=category, only_active=not include_inactive)

    return [item.model_dump(mode="json") for item in items]


@router.get("/furniture/{catalog_item_id}", response_model=Dict[str, Any])
def get_furniture_catalog_item(
    catalog_item_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a single verified furniture catalog item by catalog_item_id.
    """
    item = CatalogService.get_catalog_item(catalog_item_id, db)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Furniture catalog item '{catalog_item_id}' not found.",
        )
    return item.model_dump(mode="json")


@router.get("/bundles", response_model=List[Dict[str, Any]])
def list_furniture_bundles(
    category: Optional[str] = Query(None, description="Filter bundles by category"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    List authoritative composite furniture bundle definitions (e.g. EXECUTIVE_DESK_BUNDLE).
    """
    bundles = CatalogService.list_bundles(db, category=category)
    if not bundles:
        seed_catalog(db)
        bundles = CatalogService.list_bundles(db, category=category)

    return [b.model_dump(mode="json") for b in bundles]


@router.get("/bundles/{bundle_id}", response_model=Dict[str, Any])
def get_furniture_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a composite furniture bundle definition by bundle_id.
    """
    bundle = CatalogService.get_bundle(bundle_id, db)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Furniture bundle '{bundle_id}' not found.",
        )
    return bundle.model_dump(mode="json")


@router.get("/unregistered-assets", response_model=Dict[str, Any])
def get_unregistered_revit_assets() -> Dict[str, Any]:
    """
    Audit report of real Revit RFA files discovered in local storage
    that lack verified physical metadata in the catalog manifest.
    """
    report: AssetDiscoveryReport = scan_revit_assets()
    return {
        "total_rfa_files_found": report.total_rfa_files_found,
        "registered_items_count": report.registered_items_count,
        "unregistered_rfa_count": report.unregistered_rfa_count,
        "unregistered_assets": [a.model_dump(mode="json") for a in report.unregistered_assets],
    }


@router.post("/sync", response_model=Dict[str, Any])
def sync_catalog(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Idempotent trigger to synchronize local catalog manifest and RFA files into PostgreSQL.
    """
    stats = seed_catalog(db)
    return stats
