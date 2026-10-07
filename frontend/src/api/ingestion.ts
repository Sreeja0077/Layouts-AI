import { GeometryVerificationReport, ElementGeometry } from "../types/verification";
import {
  FloorPlanRenderModel,
  RenderWall,
  RenderDoor,
  RenderWindow,
  RenderColumn,
  RenderFurniture,
  RenderSpace,
  RenderGeometry,
  PolygonRing,
  RenderPolygon,
} from "../editor/renderer/renderTypes";

const API_BASE = "/api/v1";

export interface UploadFloorPlanParams {
  projectId: string;
  file: File;
  floorPlanName?: string;
  floorNumber?: number;
  buildingName?: string;
  floorPlanId?: string;
}

export interface IngestionStatusResponse {
  project_id: string;
  floor_plan_id: string;
  source_version_id: string;
  version_no: number;
  status: string; // "UPLOADED" | "INGESTING" | "PENDING" | "PENDING_VERIFICATION" | "VERIFIED" | "REJECTED" | "PUBLISHED" | "FAILED"
  source_type: string;
  file_name: string;
  is_published: boolean;
  geometry_elements?: {
    walls: number;
    doors: number;
    windows: number;
    columns: number;
    spaces: number;
  };
  warnings?: any[];
  verification_report?: GeometryVerificationReport;
}

export interface ProjectItem {
  id: string;
  name: string;
  client_name?: string;
  floor_plans_count?: number;
}

export interface FloorPlanItem {
  id: string;
  project_id: string;
  name: string;
  floor_number?: number;
  current_working_revision_id?: string;
}

export async function uploadFloorPlanFile(
  params: UploadFloorPlanParams,
  onProgress?: (progressPercent: number) => void
): Promise<IngestionStatusResponse> {
  const formData = new FormData();
  formData.append("file", params.file);
  if (params.floorPlanName) formData.append("floor_plan_name", params.floorPlanName);
  if (params.floorNumber !== undefined) formData.append("floor_number", params.floorNumber.toString());
  if (params.buildingName) formData.append("building_name", params.buildingName);
  if (params.floorPlanId) formData.append("floor_plan_id", params.floorPlanId);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/projects/${encodeURIComponent(params.projectId)}/floor-plans/upload`);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result = JSON.parse(xhr.responseText);
          resolve(result);
        } catch (err) {
          reject(new Error("Invalid JSON response from server upload endpoint"));
        }
      } else {
        try {
          const errData = JSON.parse(xhr.responseText);
          reject(new Error(errData.detail || `Upload failed with HTTP ${xhr.status}`));
        } catch {
          reject(new Error(`Upload failed with HTTP ${xhr.status}: ${xhr.statusText}`));
        }
      }
    };

    xhr.onerror = () => {
      reject(new Error("Network error occurred while uploading floor plan file"));
    };

    xhr.send(formData);
  });
}

export async function fetchIngestionStatus(
  projectId: string,
  floorPlanId: string
): Promise<IngestionStatusResponse> {
  const resp = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectId)}/floor-plans/${encodeURIComponent(floorPlanId)}/ingestion-status`
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch ingestion status (${resp.status})`);
  }
  return resp.json();
}

export async function publishFloorPlanVersion(
  projectId: string,
  floorPlanId: string,
  versionNo?: number
): Promise<any> {
  const resp = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectId)}/floor-plans/${encodeURIComponent(floorPlanId)}/publish`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(versionNo ? { version_no: versionNo } : {}),
    }
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Publish failed: ${resp.statusText}`);
  }
  return resp.json();
}

export async function getPublishedFloorPlanVersion(
  projectId: string,
  floorPlanId: string
): Promise<any> {
  const resp = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectId)}/floor-plans/${encodeURIComponent(floorPlanId)}/published-version`
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `No published version found: ${resp.statusText}`);
  }
  return resp.json();
}

export async function listProjects(): Promise<ProjectItem[]> {
  const resp = await fetch(`${API_BASE}/projects/`);
  if (!resp.ok) throw new Error("Failed to list projects");
  return resp.json();
}

export async function createProject(name: string, clientName?: string): Promise<ProjectItem> {
  const resp = await fetch(`${API_BASE}/projects/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, client_name: clientName }),
  });
  if (!resp.ok) throw new Error("Failed to create project");
  return resp.json();
}

export async function listFloorPlans(projectId: string): Promise<FloorPlanItem[]> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/floor-plans`);
  if (!resp.ok) throw new Error("Failed to list floor plans");
  return resp.json();
}

/** Helper to parse GeoJSON polygon/multipolygon from element geometry into RenderGeometry */
function parseRenderGeometry(elem: ElementGeometry): RenderGeometry | undefined {
  const type =
    elem.type ||
    (Array.isArray(elem.coordinates) &&
    Array.isArray(elem.coordinates[0]) &&
    Array.isArray(elem.coordinates[0][0]) &&
    Array.isArray(elem.coordinates[0][0][0])
      ? "MultiPolygon"
      : "Polygon");
  const polygons: RenderPolygon[] = [];

  if (type === "MultiPolygon" && Array.isArray(elem.coordinates)) {
    const multi = elem.coordinates as number[][][][];
    for (const polyCoords of multi) {
      if (!Array.isArray(polyCoords) || polyCoords.length === 0) continue;
      const exterior: PolygonRing = (polyCoords[0] || []).map((pt: number[]) => ({ x: pt[0], y: pt[1] }));
      const holes: PolygonRing[] = (polyCoords.slice(1) || []).map((hole: number[][]) =>
        (hole || []).map((pt: number[]) => ({ x: pt[0], y: pt[1] }))
      );
      if (exterior.length > 0) {
        polygons.push({ exterior, holes: holes.length > 0 ? holes : undefined });
      }
    }
  } else if (type === "Polygon" && Array.isArray(elem.coordinates)) {
    const polyCoords = elem.coordinates as number[][][];
    if (polyCoords.length > 0) {
      const exterior: PolygonRing = (polyCoords[0] || []).map((pt: number[]) => ({ x: pt[0], y: pt[1] }));
      const holes: PolygonRing[] = (polyCoords.slice(1) || []).map((hole: number[][]) =>
        (hole || []).map((pt: number[]) => ({ x: pt[0], y: pt[1] }))
      );
      if (exterior.length > 0) {
        polygons.push({ exterior, holes: holes.length > 0 ? holes : undefined });
      }
    }
  }

  if (polygons.length === 0 && elem.boundary && Array.isArray(elem.boundary)) {
    const pts = elem.boundary as number[][];
    if (pts.length >= 3) {
      const exterior: PolygonRing = pts.map((pt) => ({ x: pt[0], y: pt[1] }));
      polygons.push({ exterior });
    }
  }

  return polygons.length > 0 ? { polygons } : undefined;
}

/**
 * Utility to convert backend GeometryVerificationReport elements into interactive Konva FloorPlanRenderModel.
 * Accurately extracts full 2D polygon footprints from IFC/DXF geometry models.
 */
export function reportToRenderModel(report: GeometryVerificationReport): FloorPlanRenderModel {
  const walls: RenderWall[] = [];
  const doors: RenderDoor[] = [];
  const windows: RenderWindow[] = [];
  const columns: RenderColumn[] = [];
  const spaces: RenderSpace[] = [];
  const furniture: RenderFurniture[] = [];

  const allPoints: Array<{ x: number; y: number }> = [];

  // Helper to extract 2D points from GeoJSON coordinates or boundary arrays
  const extract2DPts = (elem: any): Array<{ x: number; y: number }> => {
    const pts: Array<{ x: number; y: number }> = [];
    if (Array.isArray(elem.boundary) && elem.boundary.length > 0) {
      for (const pt of elem.boundary) {
        if (Array.isArray(pt) && pt.length >= 2 && typeof pt[0] === "number" && typeof pt[1] === "number") {
          pts.push({ x: pt[0], y: pt[1] });
        }
      }
    }
    if (pts.length === 0 && elem.coordinates) {
      const flat = (elem.coordinates as any).flat(4);
      for (let i = 0; i < flat.length - 1; i += 2) {
        if (typeof flat[i] === "number" && typeof flat[i + 1] === "number") {
          pts.push({ x: flat[i], y: flat[i + 1] });
        }
      }
    }
    return pts;
  };

  (report.all_elements_geometry || []).forEach((elem, index) => {
    const cat = (elem.category || "").toUpperCase();
    const subtype = (elem.subtype || elem.category || "OTHER").toUpperCase();
    const sourceIfcType = elem.element_type || "IfcEntity";

    const pts = extract2DPts(elem);
    pts.forEach((p) => allPoints.push(p));
    const renderGeom = parseRenderGeometry(elem);

    let cleanName = elem.name || elem.element_type || elem.category || `Item ${index + 1}`;
    if (cleanName === "Polygon" || cleanName === "MultiPolygon") {
      cleanName = elem.element_type || `Item ${index + 1}`;
    }

    const centerX = pts.length > 0 ? pts.reduce((sum, p) => sum + p.x, 0) / pts.length : 0;
    const centerY = pts.length > 0 ? pts.reduce((sum, p) => sum + p.y, 0) / pts.length : 0;

    if (cat === "WALL" || cat.includes("WALL")) {
      const startPt = pts[0] || { x: 0, y: 0 };
      const endPt = pts[1] || pts[0] || { x: 0, y: 0 };
      walls.push({
        id: elem.id || elem.global_id || `wall_${index}`,
        start: startPt,
        end: endPt,
        thicknessMeters: 0.2,
        isExterior: true,
        geometry: renderGeom,
      });
    } else if (cat === "DOOR" || cat.includes("DOOR")) {
      doors.push({
        id: elem.id || elem.global_id || `door_${index}`,
        position: { x: centerX, y: centerY },
        widthMeters: 0.9,
        swingAngleDeg: 90,
        geometry: renderGeom,
      });
      furniture.push({
        id: elem.id || elem.global_id || `door_${index}`,
        catalogItemId: elem.global_id || elem.id,
        itemType: "DOOR",
        subtype: "DOOR",
        category: "FURNITURE_ITEM",
        sourceIfcType,
        name: cleanName,
        position: { x: centerX, y: centerY },
        widthMeters: 0.9,
        depthMeters: 0.2,
        rotationDeg: 0,
        isLocked: true,
        isImported: true,
        geometry: renderGeom,
        properties: elem.properties || {},
      });
    } else if (cat === "WINDOW" || cat.includes("WINDOW")) {
      const startPt = pts[0] || { x: 0, y: 0 };
      const endPt = pts[1] || pts[0] || { x: 0, y: 0 };
      windows.push({
        id: elem.id || elem.global_id || `win_${index}`,
        start: startPt,
        end: endPt,
        thicknessMeters: 0.2,
        geometry: renderGeom,
      });
      furniture.push({
        id: elem.id || elem.global_id || `win_${index}`,
        catalogItemId: elem.global_id || elem.id,
        itemType: "WINDOW",
        subtype: "WINDOW",
        category: "FURNITURE_ITEM",
        sourceIfcType,
        name: cleanName,
        position: { x: centerX, y: centerY },
        widthMeters: 1.0,
        depthMeters: 0.2,
        rotationDeg: 0,
        isLocked: true,
        isImported: true,
        geometry: renderGeom,
        properties: elem.properties || {},
      });
    } else if (cat === "COLUMN" || cat.includes("COLUMN")) {
      columns.push({
        id: elem.id || elem.global_id || `col_${index}`,
        position: { x: centerX, y: centerY },
        widthMeters: 0.6,
        heightMeters: 0.6,
        geometry: renderGeom,
      });
    } else if (cat === "SPACE" || cat.includes("SPACE") || cat.includes("ROOM")) {
      if (renderGeom) {
        spaces.push({
          id: elem.id || elem.global_id || `space_${index}`,
          name: cleanName.includes("IfcSpace") ? `Room ${spaces.length + 1}` : cleanName,
          geometry: renderGeom,
        });
      }
    } else {
      furniture.push({
        id: elem.id || elem.global_id || `furn_${index}`,
        catalogItemId: elem.global_id || elem.id,
        itemType: subtype,
        subtype,
        category: "FURNITURE_ITEM",
        sourceIfcType,
        name: cleanName,
        position: { x: centerX, y: centerY },
        widthMeters: 1.0,
        depthMeters: 0.8,
        rotationDeg: 0,
        isLocked: true,
        isImported: true,
        geometry: renderGeom,
        properties: elem.properties || {},
      });
    }
  });

  let boundaryPts: Array<{ x: number; y: number }> = [];
  if (Array.isArray(report.boundary_polygon) && report.boundary_polygon.length >= 3) {
    boundaryPts = report.boundary_polygon.map((pt) => ({ x: pt[0], y: pt[1] }));
  }

  if (boundaryPts.length === 0 && allPoints.length > 0) {
    const minX = Math.min(...allPoints.map((p) => p.x));
    const maxX = Math.max(...allPoints.map((p) => p.x));
    const minY = Math.min(...allPoints.map((p) => p.y));
    const maxY = Math.max(...allPoints.map((p) => p.y));
    const pad = 1.0;
    boundaryPts = [
      { x: minX - pad, y: minY - pad },
      { x: maxX + pad, y: minY - pad },
      { x: maxX + pad, y: maxY + pad },
      { x: minX - pad, y: maxY + pad },
    ];
  }

  if (boundaryPts.length === 0) {
    boundaryPts = [
      { x: 0, y: 0 },
      { x: 20, y: 0 },
      { x: 20, y: 15 },
      { x: 0, y: 15 },
    ];
  }

  return {
    id: report.floor_plan_name || "uploaded_fp",
    name: report.floor_plan_name || "Uploaded Floor Plan",
    boundary: boundaryPts,
    walls,
    doors,
    windows,
    columns,
    spaces,
    furniture,
  };
}
