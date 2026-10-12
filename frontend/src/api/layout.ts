import { FloorPlanRenderModel, RenderFurniture } from "../editor/renderer/renderTypes";

const API_BASE = "/api/v1";

export interface LayoutRequirementPayload {
  item_type: string;
  quantity: number;
  width_m?: number;
  depth_m?: number;
  catalog_id?: string;
}

export interface GenerateLayoutRequest {
  floor_plan_id: string;
  room_id?: string;
  storey_name?: string;
  requirements?: LayoutRequirementPayload[];
  requirement_set?: any;
  selected_region_polygon?: Array<{ x: number; y: number }>;
  existing_furniture?: any[];
  options?: {
    max_candidates?: number;
    solver_mode?: string;
    allow_internal_wall_moves?: boolean;
  };
  envelope?: boolean;
}

export interface PlacedObjectPayload {
  id: string;
  catalog_item_id: string;
  item_type: string;
  x: number;
  y: number;
  rotation_deg: number;
  width: number;
  height: number;
  clearance_front?: number;
  clearance_back?: number;
  clearance_sides?: number;
  locked?: boolean;
  source_object_id?: string;
  is_relocated?: boolean;
  is_new?: boolean;
  movability_status?: string;
}

export interface InfeasibilityReportPayload {
  is_feasible: boolean;
  candidate_count: number;
  requested_items: any[];
  selected_region_polygon?: Array<[number, number]>;
  usable_area_sqm: number;
  reasons: string[];
  violated_constraints: string[];
  max_feasible_quantity?: number;
}

export interface LayoutSuggestionPayload {
  id: string;
  floor_plan_id: string;
  room_id?: string;
  strategy_name: string;
  placed_objects: PlacedObjectPayload[];
  circulation_paths?: any[];
  explanation?: string;
  spatial_signature?: string;
  is_feasible?: boolean;
  metrics?: {
    total_seats: number;
    used_floor_area_sqm: number;
    circulation_area_sqm?: number;
    circulation_ratio?: number;
    rule_compliance_score: number;
    composite_score: number;
  };
}

export interface GenerateLayoutResponsePayload {
  success: boolean;
  candidate_count: number;
  candidates: LayoutSuggestionPayload[];
  infeasibility_report?: InfeasibilityReportPayload;
}

export async function generateLayoutCandidates(
  request: GenerateLayoutRequest
): Promise<GenerateLayoutResponsePayload> {
  const resp = await fetch(`${API_BASE}/layouts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...request, envelope: true }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to generate layout candidates (${resp.status})`);
  }

  const data = await resp.json();
  if (Array.isArray(data)) {
    return {
      success: data.length > 0,
      candidate_count: data.length,
      candidates: data,
    };
  }
  return data;
}

/** Utility to merge a generated LayoutSuggestion candidate into active FloorPlanRenderModel */
export function applySuggestionToRenderModel(
  baseModel: FloorPlanRenderModel,
  suggestion: LayoutSuggestionPayload
): FloorPlanRenderModel {
  const generatedFurniture: RenderFurniture[] = (suggestion.placed_objects || []).map((obj) => ({
    id: obj.id,
    catalogItemId: obj.catalog_item_id,
    itemType: obj.item_type,
    subtype: obj.item_type,
    category: "FURNITURE_ITEM",
    position: { x: obj.x, y: obj.y },
    widthMeters: obj.width,
    depthMeters: obj.height,
    rotationDeg: obj.rotation_deg,
    isLocked: obj.locked || obj.movability_status === "SOLD_FIXED",
    isImported: !obj.is_new,
  }));

  return {
    ...baseModel,
    furniture: generatedFurniture,
  };
}

export interface ValidateRegionRequest {
  floor_plan_id: string;
  storey_name?: string;
  world_points: Array<{ x: number; y: number }>;
}

export type RegionValidationStatus = "VALID" | "CLIPPED" | "NO_OVERLAP" | "INVALID_INPUT" | "FAILED";

export interface ValidatedRegionResponse {
  status: RegionValidationStatus;
  is_valid: boolean;
  is_clipped: boolean;
  message: string;
  floor_plan_id: string;
  storey_name?: string;
  submitted_points: Array<{ x: number; y: number }>;
  clipped_points: Array<{ x: number; y: number }>;
  clipped_polygons?: Array<Array<{ x: number; y: number }>>;
  area_sqm: number;
  perimeter_m: number;
  centroid?: { x: number; y: number } | null;
}

export async function validateRegion(
  request: ValidateRegionRequest
): Promise<ValidatedRegionResponse> {
  const resp = await fetch(`${API_BASE}/layouts/validate-region`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to validate region (${resp.status})`);
  }

  return resp.json();
}

