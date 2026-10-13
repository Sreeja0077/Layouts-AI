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
   - GET /api/v1/catalog/unregistered-assets
8. End-to-end acceptance flow:
   REAL RFA ASSET REFERENCE -> catalog registration -> persisted catalog item -> GET API -> 2D footprint data
"""

import os
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.catalog import router as catalog_router
from app.domain.catalog.manifest import scan_revit_assets, load_catalog_manifest
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
    assert item.height_m == 0.75
    assert item.category == FurnitureCategory.DESK
    assert item.clearance.front_m == 0.9


def test_furniture_catalog_item_rejects_negative_or_zero_dimensions():
    """Verify validator strictly rejects non-positive dimensions (width <= 0 or depth <= 0)."""
    with pytest.raises(ValidationError):
        FurnitureCatalogItem(
            catalog_item_id="invalid_1",
            name="Invalid Width Desk",
            category=FurnitureCategory.DESK,
            width_m=0.0,  # Invalid
            depth_m=0.8,
        )

    with pytest.raises(ValidationError):
        FurnitureCatalogItem(
            catalog_item_id="invalid_2",
            name="Negative Depth Desk",
            category=FurnitureCategory.DESK,
            width_m=1.5,
            depth_m=-0.5,  # Invalid
        )


def test_furniture_catalog_item_missing_required_fields():
    """Verify schema rejects items missing required fields."""
    with pytest.raises(ValidationError):
        # Missing width_m and depth_m
        FurnitureCatalogItem(
            catalog_item_id="missing_dims",
            name="No Dims Item",
            category=FurnitureCategory.CHAIR,
        )


# ==============================================================================
# 2. BUNDLE SCHEMA VALIDATION
# ==============================================================================

def test_bundle_schema_valid():
    """Verify FurnitureBundle creation and component placements."""
    bundle = FurnitureBundle(
        bundle_id="EXECUTIVE_DESK_BUNDLE",
        name="Executive Suite Bundle",
        category=FurnitureCategory.DESK,
        description="Desk with guest seating",
        components=[
            BundleComponentPlacement(
                component_id="desk_main",
                catalog_item_id="item_desk_01",
                quantity=1,
                relative_x_m=0.0,
                relative_y_m=0.0,
                is_primary=True,
            ),
            BundleComponentPlacement(
                component_id="chair_side",
                catalog_item_id="item_chair_01",
                quantity=2,
                relative_x_m=1.0,
                relative_y_m=0.5,
                relative_rotation_deg=180.0,
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
# 3. ASSET SCANNER & UNREGISTERED ASSET HANDLING
# ==============================================================================

def test_scan_revit_assets_discovers_rfas_and_flags_unregistered():
    """
    Verify scan_revit_assets discovers real RFA files on disk and flags
    files without verified metadata as PENDING_VERIFIED_METADATA.
    """
    report = scan_revit_assets()
    # If RFA files exist in the assets folder, report discovers them
    if report.total_rfa_files_found > 0:
        assert report.total_rfa_files_found >= 2
        # Check that unregistered files are audited with explicit reason
        for unreg in report.unregistered_assets:
            assert unreg.status in ("PENDING_VERIFIED_METADATA", "INVALID_METADATA")
            assert unreg.file_name.endswith(".rfa")
            assert len(unreg.reason) > 0


# ==============================================================================
# 4. DATABASE PERSISTENCE & IDEMPOTENT SEEDER
# ==============================================================================

def test_idempotent_catalog_seeder(in_memory_db):
    """Verify seed_catalog inserts verified items and bundles, and repeated runs do not duplicate."""
    # Run seeder 1st time
    res1 = seed_catalog(in_memory_db)
    assert res1["status"] == "SUCCESS"
    assert in_memory_db.query(FurnitureCatalogItemModel).count() >= 1

    # Run seeder 2nd time (must be idempotent)
    res2 = seed_catalog(in_memory_db)
    assert res2["status"] == "SUCCESS"
    assert res2["items_seeded"] == 0  # 0 new rows inserted
    assert res2["items_updated"] >= 1  # Updated existing rows


def test_catalog_service_queries(in_memory_db):
    """Verify CatalogService interface queries items and bundles."""
    seed_catalog(in_memory_db)
    
    # Query all
    items = CatalogService.list_catalog_items(in_memory_db)
    assert len(items) >= 1

    # Query by ID
    first_item = items[0]
    fetched = CatalogService.get_catalog_item(first_item.catalog_item_id, in_memory_db)
    assert fetched is not None
    assert fetched.catalog_item_id == first_item.catalog_item_id
    assert fetched.width_m > 0
    assert fetched.depth_m > 0

    # Query dimensions boundary for layout solvers
    dims = CatalogService.resolve_physical_dimensions(first_item.catalog_item_id, in_memory_db)
    assert dims is not None
    assert dims["width"] == first_item.width_m
    assert dims["depth"] == first_item.depth_m


# ==============================================================================
# 5. BACKEND API ENDPOINTS
# ==============================================================================

def test_api_get_catalog_furniture(api_client, in_memory_db):
    """Verify GET /api/v1/catalog/furniture returns verified items with physical dimensions."""
    response = api_client.get("/api/v1/catalog/furniture")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    item = data[0]
    assert "catalog_item_id" in item
    assert "width_m" in item
    assert "depth_m" in item
    assert item["width_m"] > 0
    assert item["depth_m"] > 0


def test_api_get_catalog_furniture_item_by_id(api_client, in_memory_db):
    """Verify GET /api/v1/catalog/furniture/{id} returns single verified item or 404."""
    list_res = api_client.get("/api/v1/catalog/furniture")
    first_id = list_res.json()[0]["catalog_item_id"]

    response = api_client.get(f"/api/v1/catalog/furniture/{first_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["catalog_item_id"] == first_id

    # Test 404 for nonexistent item
    not_found = api_client.get("/api/v1/catalog/furniture/nonexistent_xyz")
    assert not_found.status_code == 404


def test_api_get_bundles(api_client, in_memory_db):
    """Verify GET /api/v1/catalog/bundles returns composite bundle definitions."""
    response = api_client.get("/api/v1/catalog/bundles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    bundle = data[0]
    assert "bundle_id" in bundle
    assert "components" in bundle


def test_api_get_unregistered_assets(api_client):
    """Verify GET /api/v1/catalog/unregistered-assets returns audit report."""
    response = api_client.get("/api/v1/catalog/unregistered-assets")
    assert response.status_code == 200
    data = response.json()
    assert "total_rfa_files_found" in data
    assert "unregistered_assets" in data


# ==============================================================================
# 6. INTEGRATION ACCEPTANCE TEST
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
    assert len(items) >= 1

    # 3. Verify real RFA asset reference exists on item
    rfa_item = next((it for it in items if it.get("source_type") == "REVIT_RFA"), None)
    assert rfa_item is not None
    assert rfa_item["source_reference"].endswith(".rfa")

    # 4. Verify verified dimensions provide accurate 2D footprint rectangle
    width = rfa_item["width_m"]
    depth = rfa_item["depth_m"]
    assert width > 0
    assert depth > 0

    footprint_area = round(width * depth, 4)
    assert footprint_area > 0
    print(f"Verified RFA item '{rfa_item['name']}' footprint: {width}m x {depth}m (Area: {footprint_area} m²)")
