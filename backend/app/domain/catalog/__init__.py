"""
Furniture Catalog Domain Package (Phase 7 Task 7.1).
"""

from app.domain.catalog.models import (
    BundleComponentPlacement,
    ClearanceDefinition,
    FootprintGeometry,
    FurnitureBundle,
    FurnitureCatalogItem,
    FurnitureCategory,
    SourceAssetType,
)

__all__ = [
    "SourceAssetType",
    "FurnitureCategory",
    "ClearanceDefinition",
    "FootprintGeometry",
    "FurnitureCatalogItem",
    "BundleComponentPlacement",
    "FurnitureBundle",
]
