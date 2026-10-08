import { FloorPlanRenderModel, RenderFurniture } from "../editor/renderer/renderTypes";

const API_BASE = "/api/v1";

export interface LayoutRequirementPayload {
  item_type: string;
  quantity: number;
  width_m?: number;
  depth_m?: number;
}

export interface GenerateLayoutRequest {
  floor_plan_id: string;
  room_id?: string;
  requirements?: LayoutRequirementPayload[];
}

export interface PlacedObjectPayload {
  id: str;
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
}

export interface LayoutSuggestionPayload {
  id: string;
  floor_plan_id: string;
  room_id?: string;
  strategy_name: string;
  placed_objects: PlacedObjectPayload[];
  explanation?: string;
  metrics?: {
    total_seats: number;
    used_floor_area_sqm: number;
    rule_compliance_score: number;
    composite_score: number;
  };
}

export async function generateLayoutCandidates(
  request: GenerateLayoutRequest
): Promise<LayoutSuggestionPayload[]> {
  const resp = await fetch(`${API_BASE}/layouts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to generate layout candidates (${resp.status})`);
  }

  return resp.json();
}

/** Utility to merge a generated LayoutSuggestion candidate into active FloorPlanRenderModel */
export function applySuggestionToRenderModel(
  baseModel: FloorPlanRenderModel,
  suggestion: LayoutSuggestionPayload
): FloorPlanRenderModel {
  const generatedFurniture: RenderFurniture[] = suggestion.placed_objects.map((obj) => ({
    id: obj.id,
    catalogItemId: obj.catalog_item_id,
    itemType: obj.item_type,
    subtype: obj.item_type,
    category: "FURNITURE_ITEM",
    position: { x: obj.x, y: obj.y },
    widthMeters: obj.width,
    depthMeters: obj.height,
    rotationDeg: obj.rotation_deg,
    isLocked: obj.locked || false,
    isImported: false,
  }));

  // Keep structural walls, doors, windows, columns, spaces from base model and replace/add generated furniture
  const nonGeneratedFurniture = baseModel.furniture.filter((f) => f.isImported || f.isLocked);

  return {
    ...baseModel,
    furniture: [...nonGeneratedFurniture, ...generatedFurniture],
  };
}
