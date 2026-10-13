"""
Authoritative Furniture Catalog Seeder (Phase 7 Task 7.1).
Idempotently synchronizes verified catalog items and bundles into PostgreSQL.
Never fabricates unverified physical dimensions or inserts pending assets into the verified catalog.
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
    1. Discovers all RFAs on disk and matches authoritative metadata.
    2. Validates metadata (Pydantic FurnitureCatalogItem).
    3. Upserts verified items into furniture_catalog_items table.
    4. Upserts verified composite bundles into furniture_bundles table.
    5. Excludes pending and invalid assets from the verified catalog table.
    6. Distinguishes discovered, verified, inserted, updated, pending, and invalid counts.
    """
    report: AssetDiscoveryReport = scan_revit_assets(manifest_path=manifest_path)
    
    seeded_items_count = 0
    updated_items_count = 0
    seeded_bundles_count = 0
    updated_bundles_count = 0

    # 1. Upsert strictly verified catalog items
    for item in report.verified_catalog_items:
        # Extra safety guard: never insert items with non-positive dimensions
        if item.width_m <= 0 or item.depth_m <= 0:
            logger.error(
                "Skipping item %s with non-positive dimensions: %f x %f",
                item.catalog_item_id, item.width_m, item.depth_m
            )
            continue

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

    # 2. Upsert verified composite bundles
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

    pending_count = len([a for a in report.unregistered_assets if a.status == "PENDING_VERIFIED_METADATA"])
    invalid_count = len([a for a in report.unregistered_assets if a.status == "INVALID_METADATA"])

    result_summary = {
        "status": "SUCCESS",
        "discovered": report.total_rfa_files_found,
        "verified": len(report.verified_catalog_items),
        "inserted": seeded_items_count,
        "updated": updated_items_count,
        "pending": pending_count,
        "invalid": invalid_count,
        "bundles_seeded": seeded_bundles_count,
        "bundles_updated": updated_bundles_count,
        "diagnostic": report.diagnostic,
        # Backward compatibility aliases
        "total_rfa_discovered": report.total_rfa_files_found,
        "items_seeded": seeded_items_count,
        "items_updated": updated_items_count,
        "unregistered_rfa_count": report.unregistered_rfa_count,
        "unregistered_assets": [a.model_dump(mode="json") for a in report.unregistered_assets],
    }

    logger.info(
        "Seeder complete: Discovered=%d, Verified=%d (Inserted=%d, Updated=%d), Pending=%d, Invalid=%d, Bundles=%d",
        report.total_rfa_files_found,
        len(report.verified_catalog_items),
        seeded_items_count,
        updated_items_count,
        pending_count,
        invalid_count,
        seeded_bundles_count + updated_bundles_count,
    )

    return result_summary
