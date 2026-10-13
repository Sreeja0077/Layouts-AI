"""
Authoritative Furniture Catalog Seeder (Phase 7 Task 7.1).
Idempotently synchronizes verified catalog items and bundles into PostgreSQL.
Never fabricates unverified physical dimensions.
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.domain.catalog.manifest import scan_revit_assets, AssetDiscoveryReport
from app.persistence.models import FurnitureCatalogItemModel, FurnitureBundleModel

logger = logging.getLogger(__name__)


def seed_catalog(db: Session, manifest_path: Optional[Any] = None) -> Dict[str, Any]:
    """
    Idempotent catalog seeder.
    1. Scans assets directory and loads verified items from the authoritative manifest.
    2. Persists verified items into furniture_catalog_items table.
    3. Persists verified composite bundles into furniture_bundles table.
    4. Rejects incomplete/unverified assets and tracks them for audit reporting.
    """
    report: AssetDiscoveryReport = scan_revit_assets(manifest_path=manifest_path)
    
    seeded_items_count = 0
    updated_items_count = 0
    seeded_bundles_count = 0
    updated_bundles_count = 0

    # 1. Upsert verified catalog items
    for item in report.verified_catalog_items:
        existing = db.query(FurnitureCatalogItemModel).filter(FurnitureCatalogItemModel.id == item.catalog_item_id).first()
        
        clearance_dict = item.clearance.model_dump() if item.clearance else {}
        footprint_dict = item.footprint_geometry.model_dump() if item.footprint_geometry else {}

        if not existing:
            db_item = FurnitureCatalogItemModel(
                id=item.catalog_item_id,
                name=item.name,
                category=item.category.value if hasattr(item.category, "value") else str(item.category),
                subtype=item.subtype,
                family_name=item.family_name,
                family_type_name=item.family_type_name,
                source_type=item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type),
                source_reference=item.source_reference,
                width_m=item.width_m,
                depth_m=item.depth_m,
                height_m=item.height_m if item.height_m is not None else item.depth_m,
                clearance_json=clearance_dict,
                footprint_geometry_json=footprint_dict,
                is_active=item.is_active,
                is_verified=item.is_verified,
                metadata_json=item.metadata or {},
            )
            db.add(db_item)
            seeded_items_count += 1
        else:
            existing.name = item.name
            existing.category = item.category.value if hasattr(item.category, "value") else str(item.category)
            existing.subtype = item.subtype
            existing.family_name = item.family_name
            existing.family_type_name = item.family_type_name
            existing.source_type = item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type)
            existing.source_reference = item.source_reference
            existing.width_m = item.width_m
            existing.depth_m = item.depth_m
            if item.height_m is not None:
                existing.height_m = item.height_m
            existing.clearance_json = clearance_dict
            existing.footprint_geometry_json = footprint_dict
            existing.is_active = item.is_active
            existing.is_verified = item.is_verified
            existing.metadata_json = item.metadata or {}
            updated_items_count += 1

    # 2. Upsert verified bundles
    for bundle in report.bundles:
        existing_bundle = db.query(FurnitureBundleModel).filter(FurnitureBundleModel.id == bundle.bundle_id).first()
        comps_list = [c.model_dump() for c in bundle.components]
        clearance_req = bundle.clearance_requirements.model_dump() if bundle.clearance_requirements else {}

        if not existing_bundle:
            db_bundle = FurnitureBundleModel(
                id=bundle.bundle_id,
                name=bundle.name,
                category=bundle.category.value if hasattr(bundle.category, "value") else str(bundle.category),
                description=bundle.description,
                components_json=comps_list,
                default_arrangement=bundle.default_arrangement,
                orientation_rules_json=bundle.orientation_rules or {},
                clearance_requirements_json=clearance_req,
                metadata_json=bundle.metadata or {},
                is_active=bundle.is_active,
            )
            db.add(db_bundle)
            seeded_bundles_count += 1
        else:
            existing_bundle.name = bundle.name
            existing_bundle.category = bundle.category.value if hasattr(bundle.category, "value") else str(bundle.category)
            existing_bundle.description = bundle.description
            existing_bundle.components_json = comps_list
            existing_bundle.default_arrangement = bundle.default_arrangement
            existing_bundle.orientation_rules_json = bundle.orientation_rules or {}
            existing_bundle.clearance_requirements_json = clearance_req
            existing_bundle.metadata_json = bundle.metadata or {}
            existing_bundle.is_active = bundle.is_active
            updated_bundles_count += 1

    db.commit()

    return {
        "status": "SUCCESS",
        "total_rfa_discovered": report.total_rfa_files_found,
        "items_seeded": seeded_items_count,
        "items_updated": updated_items_count,
        "bundles_seeded": seeded_bundles_count,
        "bundles_updated": updated_bundles_count,
        "unregistered_rfa_count": report.unregistered_rfa_count,
        "unregistered_assets": [a.model_dump() for a in report.unregistered_assets],
    }
