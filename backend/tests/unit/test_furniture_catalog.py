"""
Unit & Integration Tests for Phase 7 Task 7.1 Furniture Catalog & Bundles.

Verifies:
1. Catalog schema validation (width, depth, clearance, metadata)
2. Required dimension validation (width > 0, depth > 0; rejecting invalid values)
3. Missing metadata rejection (RFA discovered without verified specs rejected from production catalog)
4. RFA asset reference validation
5. Bundle schema validation (composite components, cardinality, relative placement)
6. Catalog persistence & idempotent seeder
7. API endpoints:
   - GET /api/v1/catalog/furniture
   - GET /api/v1/catalog/furniture/{catalog_item_id}
   - GET /api/v1/catalog/bundles
   - GET /api/v1/catalog/bundles/{bundle_id}
   - GET /api/v1/catalog/unregistered-assets
   - POST /api/v1/catalog/sync
8. End-to-end acceptance flow:
   REAL RFA ASSET REFERENCE -> catalog registration -> persisted catalog item -> GET API -> 2D footprint data
9. Regression prevention: Exactly 29 RFAs discovered, exactly 2 verified, exactly 27 pending.
   Prevents "29 discovered but all 29 in unregistered audit" path matching bug.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.catalog import router as catalog_router
from app.domain.catalog.manifest import (
    scan_revit_assets,
    load_catalog_manifest,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_ASSETS_DIR,
)
from app.domain.catalog.models import (
    BundleComponentPlacement,
    ClearanceDefinition,
    FurnitureBundle,
    FurnitureCatalogItem,
    FurnitureCategory,
    SourceAssetType,
)
from app.domain.catalog.seeder import seed_catalog
from app.domain.catalog.catalog_service import CatalogService
from app.main import create_application
from app.persistence.database import get_db
from app.persistence.models import Base, FurnitureCatalogItemModel, FurnitureBundleModel


@pytest.fixture
def in_memory_db():
    """Isolated SQLite database for fast unit testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(in_memory_db):
    """TestClient wired to isolated in_memory_db."""
    app = create_application()

    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. CATALOG SCHEMA & DIMENSION VALIDATION
# ==============================================================================

def test_furniture_catalog_item_valid():
    """Verify clean valid creation of FurnitureCatalogItem with explicit width, depth, height."""
    item = FurnitureCatalogItem(
        catalog_item_id="item_desk_01",
        name="Executive Desk",
        category=FurnitureCategory.DESK,
        subtype="EXECUTIVE_DESK",
        family_name="Furniture_Desk",
        family_type_name="1800x900mm",
        source_type=SourceAssetType.REVIT_RFA,
        source_reference="assets/catalog/revit/desks/Furniture_Desk.rfa",
        width_m=1.8,
        depth_m=0.9,
        height_m=0.75,
        clearance=ClearanceDefinition(front_m=0.9, back_m=0.3, left_m=0.2, right_m=0.2),
        is_active=True,
        is_verified=True,
    )
    assert item.catalog_item_id == "item_desk_01"
    assert item.width_m == 1.8
    assert item.depth_m == 0.9
    assert item.category == FurnitureCategory.DESK


def test_furniture_catalog_item_rejects_negative_or_zero_dimensions():
    """Verify strictly positive dimensions (width_m > 0, depth_m > 0)."""
    with pytest.raises(ValidationError):
        FurnitureCatalogItem(
            catalog_item_id="invalid_width",
            name="Invalid Desk",
            category=FurnitureCategory.DESK,
            width_m=0.0,
            depth_m=0.8,
        )

    with pytest.raises(ValidationError):
        FurnitureCatalogItem(
            catalog_item_id="invalid_depth",
            name="Invalid Desk",
            category=FurnitureCategory.DESK,
            width_m=1.2,
            depth_m=-0.5,
        )


def test_furniture_bundle_valid():
    """Verify composite bundle creation with components and clearances."""
    bundle = FurnitureBundle(
        bundle_id="EXECUTIVE_DESK_BUNDLE",
        name="Executive Desk Bundle",
        category=FurnitureCategory.DESK,
        description="Executive desk with side storage unit",
        components=[
            BundleComponentPlacement(
                component_id="desk_main",
                catalog_item_id="rfa_autodesk_desk_standard_1500",
                quantity=1,
                relative_x_m=0.0,
                relative_y_m=0.0,
                rotation_deg=0.0,
                is_primary=True,
            ),
            BundleComponentPlacement(
                component_id="credenza_side",
                catalog_item_id="rfa_autodesk_file_cabinet_2drawer",
                quantity=2,
                relative_x_m=1.6,
                relative_y_m=0.0,
                rotation_deg=90.0,
                is_primary=False,
            ),
        ],
        default_arrangement="EXECUTIVE_SUITE",
    )
    assert bundle.bundle_id == "EXECUTIVE_DESK_BUNDLE"
    assert len(bundle.components) == 2
    assert bundle.components[0].is_primary is True
    assert bundle.components[1].quantity == 2


def test_bundle_rejects_empty_components():
    """Verify bundle requires at least one component."""
    with pytest.raises(ValidationError):
        FurnitureBundle(
            bundle_id="EMPTY_BUNDLE",
            name="Empty Bundle",
            category=FurnitureCategory.DESK,
            components=[],
        )


# ==============================================================================
# 2. ASSET SCANNER & MANIFEST MATCHING
# ==============================================================================

def test_manifest_file_exists_at_authoritative_location():
    """Verify manifest exists strictly under assets/catalog/catalog_manifest.json."""
    assert DEFAULT_MANIFEST_PATH.exists(), f"Authoritative manifest missing at {DEFAULT_MANIFEST_PATH}"
    manifest = load_catalog_manifest()
    assert len(manifest.items) >= 2
    assert len(manifest.bundles) >= 1


def test_scan_revit_assets_exact_counts_and_classification():
    """
    Verify scan_revit_assets discovers exact 29 RFA files on disk:
    - 2 verified items matched to real RFAs (Furniture_Desk.rfa, Cabinet-File 2 Drawer.rfa)
    - 27 pending assets audited with explicit missing fields
    - 0 invalid metadata items
    """
    report = scan_revit_assets()
    assert report.total_rfa_files_found == 29, f"Expected 29 RFAs discovered, got {report.total_rfa_files_found}"
    assert report.registered_items_count == 2, f"Expected 2 verified items, got {report.registered_items_count}"
    assert report.unregistered_rfa_count == 27, f"Expected 27 unregistered assets, got {report.unregistered_rfa_count}"

    # Verify verified items reference real files
    verified_ids = [it.catalog_item_id for it in report.verified_catalog_items]
    assert "rfa_autodesk_desk_standard_1500" in verified_ids
    assert "rfa_autodesk_file_cabinet_2drawer" in verified_ids

    for it in report.verified_catalog_items:
        assert it.source_reference.startswith("assets/catalog/revit/")
        assert "\\" not in it.source_reference
        assert it.width_m > 0
        assert it.depth_m > 0
        assert it.is_verified is True

    # Verify pending assets have explicit status and missing fields
    for unreg in report.unregistered_assets:
        assert unreg.status == "PENDING_VERIFIED_METADATA"
        assert unreg.file_name.endswith(".rfa")
        assert len(unreg.missing_fields) > 0
        assert "width_m" in unreg.missing_fields


def test_regression_prevention_matching_does_not_duplicate_or_orphan():
    """
    Regression test preventing bug:
    '29 discovered RFAs but only 2 catalog items because manifest/path matching is broken,
     causing all 29 RFAs to be put in unregistered audit while 2 items are registered as orphans.'
    """
    report = scan_revit_assets()
    # If matching is working, matched RFAs must NOT appear in unregistered_assets
    unregistered_filenames = [a.file_name for a in report.unregistered_assets]
    assert "Furniture_Desk.rfa" not in unregistered_filenames, "Matched RFA must not be in unregistered audit"
    assert "Cabinet-File 2 Drawer.rfa" not in unregistered_filenames, "Matched RFA must not be in unregistered audit"
    assert report.registered_items_count + report.unregistered_rfa_count == report.total_rfa_files_found


def test_stable_catalog_ids_across_repeated_scans():
    """Verify deterministic stable IDs across repeated scanner invocations."""
    report1 = scan_revit_assets()
    report2 = scan_revit_assets()
    ids1 = [i.catalog_item_id for i in report1.verified_catalog_items]
    ids2 = [i.catalog_item_id for i in report2.verified_catalog_items]
    assert ids1 == ids2


# ==============================================================================
# 3. DATABASE PERSISTENCE & IDEMPOTENT SEEDER
# ==============================================================================

def test_idempotent_catalog_seeder(in_memory_db):
    """Verify seed_catalog inserts verified items and bundles, and repeated runs do not duplicate."""
    # Run seeder 1st time
    res1 = seed_catalog(in_memory_db)
    assert res1["status"] == "SUCCESS"
    assert res1["discovered"] == 29
    assert res1["verified"] == 2
    assert res1["inserted"] == 2
    assert res1["pending"] == 27
    assert res1["invalid"] == 0
    assert in_memory_db.query(FurnitureCatalogItemModel).count() == 2
    assert in_memory_db.query(FurnitureBundleModel).count() == 1

    # Run seeder 2nd time (must be idempotent: 0 inserted, 2 updated)
    res2 = seed_catalog(in_memory_db)
    assert res2["status"] == "SUCCESS"
    assert res2["inserted"] == 0
    assert res2["updated"] == 2
    assert in_memory_db.query(FurnitureCatalogItemModel).count() == 2
    assert in_memory_db.query(FurnitureBundleModel).count() == 1


def test_catalog_service_queries(in_memory_db):
    """Verify CatalogService interface queries items and bundles."""
    seed_catalog(in_memory_db)
    
    # Query all
    items = CatalogService.list_catalog_items(in_memory_db)
    assert len(items) == 2

    # Query by ID
    desk = CatalogService.get_catalog_item("rfa_autodesk_desk_standard_1500", in_memory_db)
    assert desk is not None
    assert desk.width_m == 1.524
    assert desk.depth_m == 0.762

    # Query dimensions boundary for layout solvers
    dims = CatalogService.resolve_physical_dimensions("rfa_autodesk_desk_standard_1500", in_memory_db)
    assert dims is not None
    assert dims["width"] == 1.524
    assert dims["depth"] == 0.762


# ==============================================================================
# 4. BACKEND API ENDPOINTS
# ==============================================================================

def test_api_get_catalog_furniture(api_client, in_memory_db):
    """Verify GET /api/v1/catalog/furniture returns verified items with physical dimensions."""
    response = api_client.get("/api/v1/catalog/furniture")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    item = data[0]
    assert "catalog_item_id" in item
    assert "width_m" in item
    assert "depth_m" in item
    assert item["width_m"] > 0
    assert item["depth_m"] > 0


def test_api_get_catalog_furniture_item_by_id(api_client, in_memory_db):
    """Verify GET /api/v1/catalog/furniture/{id} returns single verified item or 404."""
    response = api_client.get("/api/v1/catalog/furniture/rfa_autodesk_desk_standard_1500")
    assert response.status_code == 200
    data = response.json()
    assert data["catalog_item_id"] == "rfa_autodesk_desk_standard_1500"
    assert data["width_m"] == 1.524

    # Test 404 for nonexistent item
    not_found = api_client.get("/api/v1/catalog/furniture/nonexistent_xyz")
    assert not_found.status_code == 404


def test_api_get_bundles(api_client, in_memory_db):
    """Verify GET /api/v1/catalog/bundles returns composite bundle definitions."""
    response = api_client.get("/api/v1/catalog/bundles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    bundle = data[0]
    assert bundle["bundle_id"] == "EXECUTIVE_DESK_BUNDLE"
    assert len(bundle["components"]) == 2


def test_api_get_unregistered_assets(api_client):
    """Verify GET /api/v1/catalog/unregistered-assets returns audit report with diagnostic counts."""
    response = api_client.get("/api/v1/catalog/unregistered-assets")
    assert response.status_code == 200
    data = response.json()
    assert data["total_rfa_files_found"] == 29
    assert data["registered_items_count"] == 2
    assert data["unregistered_rfa_count"] == 27
    assert data["pending_count"] == 27
    assert data["invalid_count"] == 0
    assert len(data["unregistered_assets"]) == 27
    assert "diagnostic" in data


def test_api_sync_catalog(api_client, in_memory_db):
    """Verify POST /api/v1/catalog/sync triggers idempotent synchronization."""
    response = api_client.post("/api/v1/catalog/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["discovered"] == 29
    assert data["verified"] == 2


# ==============================================================================
# 5. INTEGRATION ACCEPTANCE TEST
# ==============================================================================

def test_integration_rfa_to_api_to_footprint(in_memory_db, api_client):
    """
    Integration acceptance test:
    REAL RFA ASSET REFERENCE
    -> catalog registration
    -> persisted catalog item
    -> GET API
    -> 2D footprint data
    """
    # 1. Seed authoritative catalog
    seed_result = seed_catalog(in_memory_db)
    assert seed_result["status"] == "SUCCESS"

    # 2. Query API
    res = api_client.get("/api/v1/catalog/furniture")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2

    # 3. Verify real RFA asset reference exists on item
    desk_item = next((it for it in items if it.get("catalog_item_id") == "rfa_autodesk_desk_standard_1500"), None)
    assert desk_item is not None
    assert desk_item["source_reference"] == "assets/catalog/revit/desks/Furniture_Desk.rfa"

    # 4. Verify verified dimensions provide accurate 2D footprint rectangle
    width = desk_item["width_m"]
    depth = desk_item["depth_m"]
    assert width == 1.524
    assert depth == 0.762

    footprint_area = round(width * depth, 4)
    assert abs(footprint_area - 1.1613) < 0.001
