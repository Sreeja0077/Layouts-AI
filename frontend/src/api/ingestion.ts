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
function parseRenderGeometry(elem: any): RenderGeometry | undefined {
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

import { normalizeFloorPlanRenderModel } from "../geometry/coordinateNormalization";

/**
 * Utility to convert backend GeometryVerificationReport elements into interactive Konva FloorPlanRenderModel.
 * Accurately extracts full 2D polygon footprints from IFC/DXF geometry models and normalizes coordinates
 * using a single global floor-plan origin translation.
 */
export function reportToRenderModel(
  report: GeometryVerificationReport,
  requestedStorey?: string
): FloorPlanRenderModel {
  const walls: RenderWall[] = [];
  const doors: RenderDoor[] = [];
  const windows: RenderWindow[] = [];
  const columns: RenderColumn[] = [];
  const spaces: RenderSpace[] = [];
  const furniture: RenderFurniture[] = [];

  const allElements = Array.isArray(report.all_elements_geometry)
    ? report.all_elements_geometry
    : [];

  const getStoreyName = (elem: any): string | undefined =>
    elem?.storey_name ||
    elem?.properties?.storey_name ||
    undefined;

  const availableStoreys = Array.isArray(report.available_storeys)
    ? report.available_storeys
        .map((item) => item?.name)
        .filter((name): name is string => Boolean(name))
    : [];

  const targetStorey =
    requestedStorey && availableStoreys.includes(requestedStorey)
      ? requestedStorey
      : report.recommended_storey &&
          availableStoreys.includes(report.recommended_storey)
        ? report.recommended_storey
        : availableStoreys[0];

  // IFC building models can contain many storeys. A 2D floor-plan editor must render
  // one storey at a time; otherwise projecting every level onto XY creates a scattered map.
  const storeyElements =
    targetStorey && report.source_type.toUpperCase() === "IFC"
      ? allElements.filter((elem) => getStoreyName(elem) === targetStorey)
      : allElements;

  const elementsToRender = storeyElements;

  const allPoints: RenderPoint[] = [];
  const boundaryCandidatePoints: RenderPoint[] = [];

  const parseGeometryPoints = (geometry?: RenderGeometry): RenderPoint[] => {
    if (!geometry) return [];
    const points: RenderPoint[] = [];
    for (const poly of geometry.polygons || []) {
      points.push(...(poly.exterior || []));
      for (const hole of poly.holes || []) {
        points.push(...hole);
      }
    }
    return points;
  };

  const extract2DPts = (elem: any): RenderPoint[] => {
    const pts: RenderPoint[] = [];

    if (Array.isArray(elem?.boundary)) {
      for (const pt of elem.boundary) {
        if (
          Array.isArray(pt) &&
          pt.length >= 2 &&
          typeof pt[0] === "number" &&
          typeof pt[1] === "number"
        ) {
          pts.push({ x: pt[0], y: pt[1] });
        }
      }
    }

    if (pts.length === 0 && elem?.coordinates) {
      const geometry = parseRenderGeometry(elem);
      pts.push(...parseGeometryPoints(geometry));
    }

    return pts;
  };

  for (const elem of elementsToRender) {
    const cat = String(elem?.category || "").toUpperCase();
    const subtype = String(
      elem?.subtype || elem?.category || "OTHER"
    ).toUpperCase();
    const sourceIfcType = elem?.element_type || "IfcEntity";

    const pts = extract2DPts(elem);
    allPoints.push(...pts);

    const renderGeom = parseRenderGeometry(elem);
    const geometryPts = parseGeometryPoints(renderGeom);
    const renderPts = geometryPts.length > 0 ? geometryPts : pts;

    if (cat.includes("SPACE") || cat.includes("ROOM")) {
      boundaryCandidatePoints.push(...renderPts);
    }

    const centerX =
      renderPts.length > 0
        ? renderPts.reduce((sum, p) => sum + p.x, 0) / renderPts.length
        : 0;
    const centerY =
      renderPts.length > 0
        ? renderPts.reduce((sum, p) => sum + p.y, 0) / renderPts.length
        : 0;

    const cleanElementName =
      elem?.name || elem?.element_type || elem?.category || "Item";

    const storeyName = getStoreyName(elem);
    const storeyElevation =
      typeof elem?.storey_elevation_m === "number"
        ? elem.storey_elevation_m
        : typeof elem?.properties?.storey_elevation_m === "number"
          ? elem.properties.storey_elevation_m
          : undefined;

    if (cat === "WALL" || cat.includes("WALL")) {
      walls.push({
        id: elem.id || elem.global_id || `wall_${walls.length}`,
        start: pts[0] || renderPts[0] || { x: centerX, y: centerY },
        end:
          pts[1] ||
          renderPts[1] ||
          pts[0] ||
          renderPts[0] || { x: centerX, y: centerY },
        thicknessMeters: 0.2,
        isExterior: true,
        storeyName,
        storeyElevationMeters: storeyElevation,
        geometry: renderGeom,
      });
    } else if (cat === "DOOR" || cat.includes("DOOR")) {
      doors.push({
        id: elem.id || elem.global_id || `door_${doors.length}`,
        position: { x: centerX, y: centerY },
        widthMeters: 0.9,
        swingAngleDeg: 90,
        storeyName,
        storeyElevationMeters: storeyElevation,
        geometry: renderGeom,
      });
    } else if (cat === "WINDOW" || cat.includes("WINDOW")) {
      windows.push({
        id: elem.id || elem.global_id || `win_${windows.length}`,
        start: pts[0] || renderPts[0] || { x: centerX, y: centerY },
        end:
          pts[1] ||
          renderPts[1] ||
          pts[0] ||
          renderPts[0] || { x: centerX, y: centerY },
        thicknessMeters: 0.2,
        storeyName,
        storeyElevationMeters: storeyElevation,
        geometry: renderGeom,
      });
    } else if (cat === "COLUMN" || cat.includes("COLUMN")) {
      columns.push({
        id: elem.id || elem.global_id || `col_${columns.length}`,
        position: { x: centerX, y: centerY },
        widthMeters: 0.6,
        heightMeters: 0.6,
        storeyName,
        storeyElevationMeters: storeyElevation,
        geometry: renderGeom,
      });
    } else if (cat === "SPACE" || cat.includes("SPACE") || cat.includes("ROOM")) {
      if (renderGeom) {
        const rawName = String(
          elem?.name || `Room ${spaces.length + 1}`
        );
        spaces.push({
          id: elem.id || elem.global_id || `space_${spaces.length}`,
          name:
            rawName && !/^ifcspace/i.test(rawName) &&
            !/^(polygon|multipolygon)$/i.test(rawName)
              ? rawName
              : `Room ${spaces.length + 1}`,
          storeyName,
          storeyElevationMeters: storeyElevation,
          geometry: renderGeom,
        });
      }
    } else {
      // Preserve all non-structural IFC elements as imported furniture/items,
      // including BuildingElementProxy, stairs, railings, equipment, fixtures, etc.
      furniture.push({
        id: elem.id || elem.global_id || `furn_${furniture.length}`,
        catalogItemId: elem.global_id || elem.id,
        itemType: subtype,
        subtype,
        category: "FURNITURE_ITEM",
        sourceIfcType,
        name: cleanElementName,
        position: { x: centerX, y: centerY },
        widthMeters: 1.0,
        depthMeters: 0.8,
        rotationDeg: 0,
        isLocked: true,
        isImported: true,
        storeyName,
        storeyElevationMeters: storeyElevation,
        geometry: renderGeom,
        properties: elem.properties || {},
      });
    }
  }

  // The viewport boundary is the selected storey's real spatial envelope.
  // Prefer SPACE geometry; fall back to the selected storey's elements; finally
  // preserve the report's authoritative legacy boundary for DXF/no-storey cases.
  let boundaryPts: RenderPoint[] = [];

  if (boundaryCandidatePoints.length >= 3) {
    const minX = Math.min(...boundaryCandidatePoints.map((p) => p.x));
    const maxX = Math.max(...boundaryCandidatePoints.map((p) => p.x));
    const minY = Math.min(...boundaryCandidatePoints.map((p) => p.y));
    const maxY = Math.max(...boundaryCandidatePoints.map((p) => p.y));
    boundaryPts = [
      { x: minX, y: minY },
      { x: maxX, y: minY },
      { x: maxX, y: maxY },
      { x: minX, y: maxY },
    ];
  } else if (allPoints.length >= 3) {
    const minX = Math.min(...allPoints.map((p) => p.x));
    const maxX = Math.max(...allPoints.map((p) => p.x));
    const minY = Math.min(...allPoints.map((p) => p.y));
    const maxY = Math.max(...allPoints.map((p) => p.y));
    boundaryPts = [
      { x: minX, y: minY },
      { x: maxX, y: minY },
      { x: maxX, y: maxY },
      { x: minX, y: maxY },
    ];
  } else if (Array.isArray(report.boundary_polygon) && report.boundary_polygon.length >= 3) {
    boundaryPts = report.boundary_polygon.map((pt) => ({
      x: pt[0],
      y: pt[1],
    }));
  } else {
    boundaryPts = [
      { x: 0, y: 0 },
      { x: 20, y: 0 },
      { x: 20, y: 15 },
      { x: 0, y: 15 },
    ];
  }

  const rawModel: FloorPlanRenderModel = {
    id: report.floor_plan_name || "uploaded_fp",
    name: report.floor_plan_name || "Uploaded Floor Plan",
    boundary: boundaryPts,
    walls,
    doors,
    windows,
    columns,
    spaces,
    furniture,
    activeStorey: targetStorey,
    availableStoreys,
  };

  return normalizeFloorPlanRenderModel(rawModel);
}
