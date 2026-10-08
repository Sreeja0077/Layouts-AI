import {
  FloorPlanRenderModel,
  RenderPoint,
  PolygonRing,
  RenderPolygon,
  RenderGeometry,
  RenderWall,
  RenderDoor,
  RenderWindow,
  RenderColumn,
  RenderSpace,
  RenderFurniture,
} from "../editor/renderer/renderTypes";

/**
 * Calculates the single global floor-plan origin (min_x, min_y) from authoritative boundary points.
 */
export function calculateFloorPlanOrigin(boundary: RenderPoint[]): RenderPoint {
  if (!boundary || boundary.length === 0) {
    return { x: 0, y: 0 };
  }
  let minX = Infinity;
  let minY = Infinity;
  for (const pt of boundary) {
    if (typeof pt.x === "number" && !isNaN(pt.x) && pt.x < minX) minX = pt.x;
    if (typeof pt.y === "number" && !isNaN(pt.y) && pt.y < minY) minY = pt.y;
  }
  if (minX === Infinity || minY === Infinity) {
    return { x: 0, y: 0 };
  }
  return { x: minX, y: minY };
}

/** Translates a single RenderPoint by subtracting global floor-plan origin. */
export function normalizePoint(pt: RenderPoint, origin: RenderPoint): RenderPoint {
  return {
    x: Number((pt.x - origin.x).toFixed(4)),
    y: Number((pt.y - origin.y).toFixed(4)),
  };
}

/** Translates a PolygonRing loop by subtracting global floor-plan origin. */
export function normalizePolygonRing(ring: PolygonRing, origin: RenderPoint): PolygonRing {
  if (!ring || !Array.isArray(ring)) return [];
  return ring.map((pt) => normalizePoint(pt, origin));
}

/** Translates a RenderGeometry object, preserving exterior rings, interior holes, and MultiPolygons. */
export function normalizeRenderGeometry(
  geometry: RenderGeometry | undefined,
  origin: RenderPoint
): RenderGeometry | undefined {
  if (!geometry || !geometry.polygons || geometry.polygons.length === 0) {
    return geometry;
  }
  const normalizedPolygons: RenderPolygon[] = geometry.polygons.map((poly) => ({
    exterior: normalizePolygonRing(poly.exterior, origin),
    holes: poly.holes ? poly.holes.map((hole) => normalizePolygonRing(hole, origin)) : undefined,
  }));
  return { polygons: normalizedPolygons };
}

/**
 * Normalizes an entire FloorPlanRenderModel using ONE global floor-plan origin translation.
 * All render-model coordinates become local floor-plan metres starting at (0, 0) after subtracting worldOrigin.
 */
export function normalizeFloorPlanRenderModel(model: FloorPlanRenderModel): FloorPlanRenderModel {
  if (!model) return model;

  // 1. Calculate single global floor-plan origin from authoritative boundary
  const origin = calculateFloorPlanOrigin(model.boundary);

  // If model is already normalized at (0, 0), return model with worldOrigin set
  if (Math.abs(origin.x) < 1e-6 && Math.abs(origin.y) < 1e-6) {
    return {
      ...model,
      worldOrigin: { x: 0, y: 0 },
    };
  }

  // 2. Normalize boundary polygon
  const normalizedBoundary = model.boundary.map((pt) => normalizePoint(pt, origin));

  // 3. Normalize walls
  const normalizedWalls: RenderWall[] = (model.walls || []).map((wall) => ({
    ...wall,
    start: wall.start ? normalizePoint(wall.start, origin) : undefined,
    end: wall.end ? normalizePoint(wall.end, origin) : undefined,
    geometry: normalizeRenderGeometry(wall.geometry, origin),
  }));

  // 4. Normalize doors
  const normalizedDoors: RenderDoor[] = (model.doors || []).map((door) => ({
    ...door,
    position: normalizePoint(door.position, origin),
    geometry: normalizeRenderGeometry(door.geometry, origin),
  }));

  // 5. Normalize windows
  const normalizedWindows: RenderWindow[] = (model.windows || []).map((win) => ({
    ...win,
    start: win.start ? normalizePoint(win.start, origin) : undefined,
    end: win.end ? normalizePoint(win.end, origin) : undefined,
    geometry: normalizeRenderGeometry(win.geometry, origin),
  }));

  // 6. Normalize columns
  const normalizedColumns: RenderColumn[] = (model.columns || []).map((col) => ({
    ...col,
    position: normalizePoint(col.position, origin),
    geometry: normalizeRenderGeometry(col.geometry, origin),
  }));

  // 7. Normalize spaces
  const normalizedSpaces: RenderSpace[] = (model.spaces || []).map((space) => ({
    ...space,
    geometry: normalizeRenderGeometry(space.geometry, origin)!,
  }));

  // 8. Normalize furniture (both imported non-structural items and generated objects)
  const normalizedFurniture: RenderFurniture[] = (model.furniture || []).map((item) => ({
    ...item,
    position: normalizePoint(item.position, origin),
    geometry: normalizeRenderGeometry(item.geometry, origin),
  }));

  return {
    ...model,
    boundary: normalizedBoundary,
    walls: normalizedWalls,
    doors: normalizedDoors,
    windows: normalizedWindows,
    columns: normalizedColumns,
    spaces: normalizedSpaces,
    furniture: normalizedFurniture,
    worldOrigin: origin,
  };
}
