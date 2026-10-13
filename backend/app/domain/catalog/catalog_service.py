"""
Authoritative Furniture Catalog Access Service (Phase 7 Task 7.1).
Provides the clean boundary/interface for geometry engines, layout solvers,
and API routers to consume authoritative physical catalog definitions.

CRITICAL INVARIANT:
Geometry code and solvers consume catalog physical specifications from this boundary
rather than maintaining isolated hardcoded production catalogs.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.domain.catalog.models import (
    ClearanceDefinition,
    FootprintGeometry,
    FurnitureBundle,
    FurnitureCatalogItem,
    FurnitureCategory,
    SourceAssetType,
)
from app.persistence.models import FurnitureCatalogItemModel, FurnitureBundleModel


class CatalogService:
    """Authoritative catalog domain access service."""

    @staticmethod
    def get_catalog_item(catalog_item_id: str, db: Session) -> Optional[FurnitureCatalogItem]:
        """Fetch a single verified catalog item by ID from authoritative PostgreSQL store."""
        row = db.query(FurnitureCatalogItemModel).filter(FurnitureCatalogItemModel.id == catalog_item_id).first()
        if not row:
            return None
        return CatalogService._model_to_domain(row)

    @staticmethod
    def list_catalog_items(
        db: Session,
        category: Optional[str] = None,
        only_active: bool = True,
    ) -> List[FurnitureCatalogItem]:
        """Query catalog items with optional category filtering."""
        query = db.query(FurnitureCatalogItemModel)
        if only_active:
            query = query.filter(FurnitureCatalogItemModel.is_active == True)
        if category:
            cat_upper = category.upper()
            query = query.filter(FurnitureCatalogItemModel.category == cat_upper)

        rows = query.order_by(FurnitureCatalogItemModel.category, FurnitureCatalogItemModel.name).all()
        return [CatalogService._model_to_domain(r) for r in rows]

    @staticmethod
    def get_bundle(bundle_id: str, db: Session) -> Optional[FurnitureBundle]:
        """Fetch a composite furniture bundle definition by ID."""
        row = db.query(FurnitureBundleModel).filter(FurnitureBundleModel.id == bundle_id).first()
        if not row:
            return None
        return FurnitureBundle(
            bundle_id=row.id,
            name=row.name,
            category=FurnitureCategory(row.category) if row.category in FurnitureCategory.__members__ else FurnitureCategory.OTHER,
            description=row.description,
            components=row.components_json or [],
            default_arrangement=row.default_arrangement or "STANDARD",
            orientation_rules=row.orientation_rules_json or {},
            clearance_requirements=ClearanceDefinition.model_validate(row.clearance_requirements_json) if row.clearance_requirements_json else None,
            is_active=row.is_active,
            metadata=row.metadata_json or {},
        )

    @staticmethod
    def list_bundles(db: Session, category: Optional[str] = None) -> List[FurnitureBundle]:
        """List all composite furniture bundle definitions."""
        query = db.query(FurnitureBundleModel).filter(FurnitureBundleModel.is_active == True)
        if category:
            query = query.filter(FurnitureBundleModel.category == category.upper())
        rows = query.order_by(FurnitureBundleModel.category, FurnitureBundleModel.name).all()
        results = []
        for row in rows:
            results.append(
                FurnitureBundle(
                    bundle_id=row.id,
                    name=row.name,
                    category=FurnitureCategory(row.category) if row.category in FurnitureCategory.__members__ else FurnitureCategory.OTHER,
                    description=row.description,
                    components=row.components_json or [],
                    default_arrangement=row.default_arrangement or "STANDARD",
                    orientation_rules=row.orientation_rules_json or {},
                    clearance_requirements=ClearanceDefinition.model_validate(row.clearance_requirements_json) if row.clearance_requirements_json else None,
                    is_active=row.is_active,
                    metadata=row.metadata_json or {},
                )
            )
        return results

    @staticmethod
    def resolve_physical_dimensions(
        identifier: str,
        db: Session,
    ) -> Optional[Dict[str, Any]]:
        """
        Boundary method for geometry solvers:
        Resolves width, depth, and clearance from authoritative database.
        Returns None if item is not found in database.
        """
        item = CatalogService.get_catalog_item(identifier, db)
        if not item:
            return None
        return {
            "width": item.width_m,
            "depth": item.depth_m,
            "height": item.height_m,
            "clearance_back": item.clearance.back_m if item.clearance else 0.5,
            "clearance_front": item.clearance.front_m if item.clearance else 0.8,
            "clearance_sides": item.clearance.left_m if item.clearance else 0.2,
            "category": item.category.value if hasattr(item.category, "value") else str(item.category),
            "subtype": item.subtype,
            "source_reference": item.source_reference,
            "is_verified": item.is_verified,
        }

    @staticmethod
    def _model_to_domain(row: FurnitureCatalogItemModel) -> FurnitureCatalogItem:
        """Convert SQLAlchemy FurnitureCatalogItemModel to domain FurnitureCatalogItem."""
        # Convert category string safely
        cat_str = (row.category or "OTHER").upper()
        category_enum = FurnitureCategory.OTHER
        if cat_str in FurnitureCategory.__members__:
            category_enum = FurnitureCategory[cat_str]

        # Use depth_m, falling back to legacy height_m if depth_m is null
        depth_val = float(row.depth_m) if row.depth_m is not None else float(row.height_m)
        width_val = float(row.width_m)
        height_val = float(row.height_m) if row.height_m is not None else None

        clearance_data = row.clearance_json or {}
        clearance_def = ClearanceDefinition(
            front_m=float(clearance_data.get("front", clearance_data.get("front_m", 0.8))),
            back_m=float(clearance_data.get("back", clearance_data.get("back_m", 0.2))),
            left_m=float(clearance_data.get("left", clearance_data.get("left_m", clearance_data.get("sides", 0.2)))),
            right_m=float(clearance_data.get("right", clearance_data.get("right_m", clearance_data.get("sides", 0.2)))),
        )

        footprint_def = None
        if row.footprint_geometry_json:
            footprint_def = FootprintGeometry.model_validate(row.footprint_geometry_json)

        return FurnitureCatalogItem(
            catalog_item_id=row.id,
            name=row.name,
            category=category_enum,
            subtype=row.subtype,
            family_name=row.family_name,
            family_type_name=row.family_type_name,
            source_type=SourceAssetType(row.source_type) if row.source_type in SourceAssetType.__members__ else SourceAssetType.REVIT_RFA,
            source_reference=row.source_reference,
            width_m=width_val,
            depth_m=depth_val,
            height_m=height_val,
            footprint_geometry=footprint_def,
            clearance=clearance_def,
            is_active=row.is_active,
            is_verified=row.is_verified,
            metadata=row.metadata_json or {},
        )
