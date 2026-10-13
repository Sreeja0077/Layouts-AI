"""
Authoritative Furniture Catalog Manifest & Revit Asset Scanner (Phase 7 Task 7.1).

INVARIANTS:
1. Deterministic asset-to-specification binding.
2. Zero fabricated dimensions: RFA files without verified metadata are rejected or
   flagged as PENDING_VERIFIED_METADATA rather than inventing dimensions.
3. Supports consolidated catalog_manifest.json and optional per-asset sidecar metadata.
4. One authoritative manifest path: assets/catalog/catalog_manifest.json (normalized forward slashes).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.catalog.models import (
    FurnitureBundle,
    FurnitureCatalogItem,
    FurnitureCategory,
    SourceAssetType,
)

logger = logging.getLogger(__name__)

# Default repository paths for catalog assets - strictly assets/catalog/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
DEFAULT_MANIFEST_PATH = _REPO_ROOT / "assets" / "catalog" / "catalog_manifest.json"
DEFAULT_ASSETS_DIR = _REPO_ROOT / "assets" / "catalog" / "revit"


def _canonical_repo_rel_path(path: Path, root: Path) -> str:
    """
    Compute a normalized relative path from repository root, resilient to Windows
    drive letter casing disparities (e.g. 'd:\\' vs 'D:\\') and backslash variations.
    """
    try:
        norm_path = str(path.resolve()).replace("\\", "/")
        norm_root = str(root.resolve()).replace("\\", "/")
        if norm_path.lower().startswith(norm_root.lower() + "/"):
            return norm_path[len(norm_root) + 1:]
        return path.relative_to(root).as_posix()
    except Exception:
        # Fallback to posix path from current path parts
        parts = path.parts
        if "assets" in parts:
            idx = parts.index("assets")
            return "/".join(parts[idx:])
        return path.name


class UnregisteredAsset(BaseModel):
    """An RFA file discovered in local storage without verified metadata or failing validation."""
    model_config = ConfigDict(extra="ignore")

    file_name: str
    relative_path: str
    full_path: str
    file_size_bytes: int
    status: str = "PENDING_VERIFIED_METADATA"  # "PENDING_VERIFIED_METADATA" | "INVALID_METADATA"
    reason: str = "No verified physical dimensions or Revit type specification provided in catalog manifest."
    missing_fields: List[str] = Field(default_factory=lambda: ["width_m", "depth_m", "family_name", "family_type_name", "category"])


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
    diagnostic: Dict[str, Any] = Field(default_factory=dict)


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
    Uses strictly assets/catalog/catalog_manifest.json by default.
    Returns empty manifest if file does not exist yet.
    """
    path = manifest_path or DEFAULT_MANIFEST_PATH
    if not path.exists():
        logger.warning(f"Authoritative catalog manifest not found at {path}, returning empty manifest.")
        return CatalogManifest()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        manifest = CatalogManifest.model_validate(data)
        logger.info(
            f"Loaded catalog manifest from {path}: {len(manifest.items)} items, {len(manifest.bundles)} bundles"
        )
        return manifest
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
    
    INVARIANTS:
    1. Every RFA is classified as exactly one of:
       - VERIFIED (in verified_catalog_items)
       - PENDING_VERIFIED_METADATA (in unregistered_assets)
       - INVALID_METADATA (in unregistered_assets)
    2. Zero fabricated dimensions or synthetic geometry.
    3. Resilient cross-platform path matching (Windows/Linux).
    """
    target_dir = assets_dir or DEFAULT_ASSETS_DIR
    manifest_file = manifest_path or DEFAULT_MANIFEST_PATH
    manifest = load_catalog_manifest(manifest_file)
    
    # Map manifest items by multiple normalized lookup keys for bulletproof matching
    manifest_by_full_ref: Dict[str, Dict[str, Any]] = {}
    manifest_by_revit_rel: Dict[str, Dict[str, Any]] = {}
    manifest_by_filename: Dict[str, Dict[str, Any]] = {}
    
    for item_data in manifest.items:
        raw_ref = str(item_data.get("source_reference", "")).replace("\\", "/").strip()
        if not raw_ref:
            continue
        ref_lower = raw_ref.lower()
        manifest_by_full_ref[ref_lower] = item_data
        
        # Also key by path relative to 'assets/catalog/revit/'
        if "assets/catalog/revit/" in ref_lower:
            revit_rel = ref_lower.split("assets/catalog/revit/")[-1]
            manifest_by_revit_rel[revit_rel] = item_data
        elif "catalog/revit/" in ref_lower:
            revit_rel = ref_lower.split("catalog/revit/")[-1]
            manifest_by_revit_rel[revit_rel] = item_data

        # Also key by base filename
        filename_key = Path(raw_ref).name.lower()
        if filename_key:
            manifest_by_filename[filename_key] = item_data

    verified_items: List[FurnitureCatalogItem] = []
    unregistered: List[UnregisteredAsset] = []
    matched_rfa_paths = set()
    invalid_rfa_count = 0
    matched_verified_count = 0

    # Discover real RFA files on disk
    discovered_rfa_paths: List[Path] = []
    if target_dir.exists():
        discovered_rfa_paths = sorted(list(target_dir.rglob("*.rfa")), key=lambda p: str(p).lower())

    for rfa_path in discovered_rfa_paths:
        rel_to_repo = _canonical_repo_rel_path(rfa_path, _REPO_ROOT)
        norm_rel = rel_to_repo.lower()
        rfa_filename_lower = rfa_path.name.lower()

        # Lookup in manifest items: full path first, then revit subpath, then filename
        matched_spec: Optional[Dict[str, Any]] = manifest_by_full_ref.get(norm_rel)
        if not matched_spec and "assets/catalog/revit/" in norm_rel:
            subpath = norm_rel.split("assets/catalog/revit/")[-1]
            matched_spec = manifest_by_revit_rel.get(subpath)
        if not matched_spec:
            matched_spec = manifest_by_filename.get(rfa_filename_lower)

        # Check per-file sidecar metadata: [filename].metadata.json if not found in manifest
        sidecar_path = rfa_path.with_suffix(".metadata.json")
        if not matched_spec and sidecar_path.exists():
            try:
                with open(sidecar_path, "r", encoding="utf-8") as sf:
                    matched_spec = json.load(sf)
            except Exception as e:
                logger.warning(f"Failed to read sidecar metadata {sidecar_path}: {e}")

        if matched_spec:
            matched_rfa_paths.add(norm_rel)
            # Clone spec to avoid mutating input dictionary
            spec_copy = dict(matched_spec)
            # Ensure normalized canonical source_reference points to assets/catalog/revit/...
            if not spec_copy.get("source_reference") or "\\" in str(spec_copy.get("source_reference")):
                spec_copy["source_reference"] = rel_to_repo.replace("\\", "/")

            try:
                validated_item = FurnitureCatalogItem.model_validate(spec_copy)
                verified_items.append(validated_item)
                matched_verified_count += 1
            except Exception as exc:
                invalid_rfa_count += 1
                unregistered.append(
                    UnregisteredAsset(
                        file_name=rfa_path.name,
                        relative_path=rel_to_repo,
                        full_path=str(rfa_path),
                        file_size_bytes=rfa_path.stat().st_size,
                        status="INVALID_METADATA",
                        reason=f"Manifest metadata validation failed: {str(exc)}",
                        missing_fields=["valid_dimensions", "valid_category"],
                    )
                )
        else:
            # Asset genuinely lacks verified metadata: audited as PENDING_VERIFIED_METADATA
            unregistered.append(
                UnregisteredAsset(
                    file_name=rfa_path.name,
                    relative_path=rel_to_repo,
                    full_path=str(rfa_path),
                    file_size_bytes=rfa_path.stat().st_size,
                    status="PENDING_VERIFIED_METADATA",
                    reason="No verified physical dimensions (width_m, depth_m) or Revit family type specification provided in catalog manifest.",
                    missing_fields=["width_m", "depth_m", "family_name", "family_type_name", "category"],
                )
            )

    # Register any manifest items that exist independently with valid dimensions
    # and were not already matched to an on-disk RFA
    for item_data in manifest.items:
        item_id = item_data.get("catalog_item_id")
        raw_ref = str(item_data.get("source_reference", "")).replace("\\", "/").lower()
        already_verified = any(v.catalog_item_id == item_id for v in verified_items)
        if not already_verified:
            try:
                val_item = FurnitureCatalogItem.model_validate(item_data)
                verified_items.append(val_item)
            except Exception as exc:
                logger.warning(f"Independent manifest item validation failed ({item_id}): {exc}")

    # Validate bundles
    verified_bundles: List[FurnitureBundle] = []
    for bundle_data in manifest.bundles:
        try:
            val_bundle = FurnitureBundle.model_validate(bundle_data)
            verified_bundles.append(val_bundle)
        except Exception as exc:
            logger.warning(f"Bundle validation failed ({bundle_data.get('bundle_id')}): {exc}")

    diagnostic_info = {
        "manifest_path_used": str(manifest_file.resolve()).replace("\\", "/"),
        "manifest_items_count": len(manifest.items),
        "manifest_bundles_count": len(manifest.bundles),
        "rfa_files_discovered": len(discovered_rfa_paths),
        "matched_verified_count": matched_verified_count,
        "unmatched_pending_count": len([u for u in unregistered if u.status == "PENDING_VERIFIED_METADATA"]),
        "invalid_metadata_count": invalid_rfa_count,
    }

    logger.info(
        "Catalog scanner diagnostic: Discovered=%d RFAs, Verified=%d, Pending=%d, Invalid=%d, Bundles=%d",
        len(discovered_rfa_paths),
        len(verified_items),
        diagnostic_info["unmatched_pending_count"],
        invalid_rfa_count,
        len(verified_bundles),
    )

    return AssetDiscoveryReport(
        total_rfa_files_found=len(discovered_rfa_paths),
        registered_items_count=len(verified_items),
        unregistered_rfa_count=len(unregistered),
        verified_catalog_items=verified_items,
        unregistered_assets=unregistered,
        bundles_count=len(verified_bundles),
        bundles=verified_bundles,
        diagnostic=diagnostic_info,
    )
