/**
 * Furniture Catalog API Client (Phase 7 Task 7.1).
 * Communicates with FastAPI backend for authoritative verified catalog items,
 * composite bundles, and local RFA discovery audit records.
 *
 * CRITICAL: Zero hardcoded production furniture catalogs in TypeScript.
 */

const API_BASE = "http://localhost:8000/api/v1";

export interface ClearanceSpec {
  front_m: number;
  back_m: number;
  left_m: number;
  right_m: number;
}

export interface CatalogFurnitureItem {
  catalog_item_id: string;
  name: string;
  category: string;
  subtype?: string;
  family_name?: string;
  family_type_name?: string;
  source_type: string;
  source_reference?: string;
  width_m: number;
  depth_m: number;
  height_m?: number;
  clearance?: ClearanceSpec;
  is_active: boolean;
  is_verified: boolean;
  metadata?: Record<string, any>;
}

export interface BundleComponent {
  component_id: string;
  catalog_item_id: string;
  quantity: number;
  relative_x_m: number;
  relative_y_m: number;
  relative_rotation_deg: number;
  is_primary: boolean;
}

export interface CatalogBundle {
  bundle_id: string;
  name: string;
  category: string;
  description?: string;
  default_arrangement: string;
  components: BundleComponent[];
  clearance_requirements?: ClearanceSpec;
  orientation_rules?: Record<string, any>;
  is_active: boolean;
  metadata?: Record<string, any>;
}

export interface UnregisteredAsset {
  file_name: string;
  relative_path: string;
  full_path: string;
  file_size_bytes: number;
  status: string;
  reason: string;
}

export interface UnregisteredAssetsResponse {
  total_rfa_files_found: number;
  registered_items_count: number;
  unregistered_rfa_count: number;
  unregistered_assets: UnregisteredAsset[];
}

/**
 * Fetch authoritative verified furniture catalog items from backend.
 */
export async function fetchCatalogFurniture(category?: string): Promise<CatalogFurnitureItem[]> {
  const url = new URL(`${API_BASE}/catalog/furniture`);
  if (category && category !== "ALL") {
    url.searchParams.append("category", category);
  }
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch furniture catalog: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch a single verified catalog item by ID.
 */
export async function fetchCatalogItem(catalogItemId: string): Promise<CatalogFurnitureItem> {
  const response = await fetch(`${API_BASE}/catalog/furniture/${encodeURIComponent(catalogItemId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch catalog item '${catalogItemId}': ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch composite furniture bundle definitions.
 */
export async function fetchCatalogBundles(category?: string): Promise<CatalogBundle[]> {
  const url = new URL(`${API_BASE}/catalog/bundles`);
  if (category && category !== "ALL") {
    url.searchParams.append("category", category);
  }
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch furniture bundles: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch audit of local Revit RFA files discovered that lack verified metadata.
 */
export async function fetchUnregisteredAssets(): Promise<UnregisteredAssetsResponse> {
  const response = await fetch(`${API_BASE}/catalog/unregistered-assets`);
  if (!response.ok) {
    throw new Error(`Failed to fetch unregistered assets audit: ${response.statusText}`);
  }
  return response.json();
}
