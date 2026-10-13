"""
Authoritative Furniture Catalog Manifest & Revit Asset Scanner (Phase 7 Task 7.1).

INVARIANTS:
1. Deterministic asset-to-specification binding.
2. Zero fabricated dimensions: RFA files without verified metadata are rejected or
   flagged as PENDING_VERIFICATION rather than inventing dimensions.
3. Supports both consolidated catalog_manifest.json and per-asset metadata.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from app.domain.catalog.models import (
    FurnitureBundle,
    FurnitureCatalogItem,
    FurnitureCategory,
    SourceAssetType,
)

logger = logging.getLogger(__name__)

# Default repository paths for catalog assets
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
DEFAULT_MANIFEST_PATH = _REPO_ROOT / "assets" / "catalog" / "catalog_manifest.json"
DEFAULT_ASSETS_DIR = _REPO_ROOT / "assets" / "catalog" / "revit"


class UnregisteredAsset(BaseModel):
    """An RFA file discovered in local storage without verified metadata."""
    model_config = ConfigDict(extra="ignore")

    file_name: str
    relative_path: str
    full_path: str
    file_size_bytes: int
    status: str = "PENDING_VERIFIED_METADATA"
    reason: str = "No verified physical dimensions or Revit type specification provided in catalog manifest."


class AssetDiscoveryReport(BaseModel):
    """Authoritative audit of discovered assets vs verified registered catalog items."""
    model_config = ConfigDict(extra="ignore")

    total_rfa_files_found: int = 0
    registered_items_count: int = 0
    unregistered_rfa_count: int = 0
    verified_catalog_items: List[FurnitureCatalogItem] = Field(default_factory=list)
    unregistered_assets: List[UnregisteredAsset] = Field(default_factory=list)
    bundles_count: int = 0
    bundles: List[FurnitureBundle] = Field(default_factory=list)


class CatalogManifest(BaseModel):
    """Schema for the authoritative catalog manifest file."""
    model_config = ConfigDict(extra="ignore")

    version: str = "1.0.0"
    description: str = "Authoritative Revit Furniture Catalog & Bundles Manifest"
    items: List[Dict[str, Any]] = Field(default_factory=list)
    bundles: List[Dict[str, Any]] = Field(default_factory=list)


def load_catalog_manifest(manifest_path: Optional[Path] = None) -> CatalogManifest:
    """
    Load the authoritative catalog manifest from JSON.
    Returns empty manifest if file does not exist yet.
    """
    path = manifest_path or DEFAULT_MANIFEST_PATH
    if not path.exists():
        # Fallback check under assests/ if directory has alternate spelling
        alt_path = _REPO_ROOT / "assests" / "catalog" / "catalog_manifest.json"
        if alt_path.exists():
            path = alt_path

    if not path.exists():
        logger.info(f"Catalog manifest not found at {path}, returning empty manifest.")
        return CatalogManifest()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CatalogManifest.model_validate(data)
    except Exception as exc:
        logger.error(f"Failed to load catalog manifest from {path}: {exc}")
        raise ValueError(f"Invalid catalog manifest at {path}: {str(exc)}") from exc


def scan_revit_assets(
    assets_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> AssetDiscoveryReport:
    """
    Scans the local filesystem for real Revit RFA files under assets/catalog/revit/
    and matches them against authoritative catalog metadata.
    
    Rejects/flags any RFA file whose physical dimensions or metadata are unverified.
    """
    target_dir = assets_dir or DEFAULT_ASSETS_DIR
    if not target_dir.exists():
        # Fallback check under assests/
        alt_dir = _REPO_ROOT / "assests" / "catalog" / "revit"
        if alt_dir.exists():
            target_dir = alt_dir

    manifest = load_catalog_manifest(manifest_path)
    
    # Map manifest items by their normalized source_reference
    manifest_items_by_ref: Dict[str, Dict[str, Any]] = {}
    manifest_items_by_id: Dict[str, Dict[str, Any]] = {}
    
    for item_data in manifest.items:
        item_id = item_data.get("catalog_item_id")
        if item_id:
            manifest_items_by_id[item_id] = item_data
        ref = item_data.get("source_reference", "").replace("\\", "/").lower()
        if ref:
            manifest_items_by_ref[ref] = item_data

    verified_items: List[FurnitureCatalogItem] = []
    unregistered: List[UnregisteredAsset] = []
    registered_source_refs = set()

    # Discover real RFA files on disk
    discovered_rfa_paths: List[Path] = []
    if target_dir.exists():
        discovered_rfa_paths = list(target_dir.rglob("*.rfa"))

    for rfa_path in sorted(discovered_rfa_paths, key=lambda p: str(p)):
        try:
            rel_to_repo = rfa_path.relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            rel_to_repo = rfa_path.name

        norm_rel = rel_to_repo.lower()
        # Also test alternate spelling without 'assests'
        norm_rel_alt = norm_rel.replace("assests/", "assets/")

        matched_spec = manifest_items_by_ref.get(norm_rel) or manifest_items_by_ref.get(norm_rel_alt)
        
        # Check per-file sidecar metadata: [filename].metadata.json
        sidecar_path = rfa_path.with_suffix(".metadata.json")
        if not matched_spec and sidecar_path.exists():
            try:
                with open(sidecar_path, "r", encoding="utf-8") as sf:
                    matched_spec = json.load(sf)
            except Exception as e:
                logger.warning(f"Failed to read sidecar metadata {sidecar_path}: {e}")

        if matched_spec:
            # Validate required dimensions
            try:
                # Ensure source reference is set accurately
                if "source_reference" not in matched_spec or not matched_spec["source_reference"]:
                    matched_spec["source_reference"] = rel_to_repo

                validated_item = FurnitureCatalogItem.model_validate(matched_spec)
                verified_items.append(validated_item)
                registered_source_refs.add(norm_rel)
                registered_source_refs.add(norm_rel_alt)
            except Exception as exc:
                unregistered.append(
                    UnregisteredAsset(
                        file_name=rfa_path.name,
                        relative_path=rel_to_repo,
                        full_path=str(rfa_path),
                        file_size_bytes=rfa_path.stat().st_size,
                        status="INVALID_METADATA",
                        reason=f"Manifest metadata validation failed: {str(exc)}",
                    )
                )
        else:
            unregistered.append(
                UnregisteredAsset(
                    file_name=rfa_path.name,
                    relative_path=rel_to_repo,
                    full_path=str(rfa_path),
                    file_size_bytes=rfa_path.stat().st_size,
                    status="PENDING_VERIFIED_METADATA",
                    reason="No verified physical dimensions or Revit type specification provided in catalog manifest.",
                )
            )

    # Also register any manifest items that exist independently with valid dimensions
    for item_data in manifest.items:
        ref = item_data.get("source_reference", "").replace("\\", "/").lower()
        if ref and ref not in registered_source_refs:
            try:
                val_item = FurnitureCatalogItem.model_validate(item_data)
                # Check that we haven't already added this ID
                if not any(v.catalog_item_id == val_item.catalog_item_id for v in verified_items):
                    verified_items.append(val_item)
            except Exception as exc:
                logger.warning(f"Manifest item validation failed: {exc}")

    # Validate bundles
    verified_bundles: List[FurnitureBundle] = []
    for bundle_data in manifest.bundles:
        try:
            val_bundle = FurnitureBundle.model_validate(bundle_data)
            verified_bundles.append(val_bundle)
        except Exception as exc:
            logger.warning(f"Bundle validation failed: {exc}")

    return AssetDiscoveryReport(
        total_rfa_files_found=len(discovered_rfa_paths),
        registered_items_count=len(verified_items),
        unregistered_rfa_count=len(unregistered),
        verified_catalog_items=verified_items,
        unregistered_assets=unregistered,
        bundles_count=len(verified_bundles),
        bundles=verified_bundles,
    )
