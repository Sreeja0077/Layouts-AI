import { GeometryVerificationReport } from "../types/verification";
import { FloorPlanRenderModel, RenderWall, RenderDoor, RenderWindow, RenderColumn, RenderFurniture } from "../editor/renderer/renderTypes";

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

/**
 * Utility to convert backend GeometryVerificationReport elements into interactive Konva FloorPlanRenderModel.
 */
export function reportToRenderModel(report: GeometryVerificationReport): FloorPlanRenderModel {
  const boundaryPts = (report.boundary_polygon || []).map((pt) => ({ x: pt[0], y: pt[1] }));
  const walls: RenderWall[] = [];
  const doors: RenderDoor[] = [];
  const windows: RenderWindow[] = [];
  const columns: RenderColumn[] = [];
  const furniture: RenderFurniture[] = [];

  (report.all_elements_geometry || []).forEach((elem) => {
    const cat = (elem.category || "").toUpperCase();
    const coords = elem.coordinates;

    if (cat === "WALL" && Array.isArray(coords)) {
      // Flatten coords if needed to get start/end
      const pts = (coords as any).flat(3);
      if (pts.length >= 4) {
        walls.push({
          id: elem.id || elem.global_id || `wall_${walls.length}`,
          start: { x: pts[0], y: pts[1] },
          end: { x: pts[2], y: pts[3] },
          thicknessMeters: 0.2,
          isExterior: true,
        });
      }
    } else if (cat === "DOOR" && Array.isArray(coords)) {
      const pts = (coords as any).flat(3);
      if (pts.length >= 2) {
        doors.push({
          id: elem.id || elem.global_id || `door_${doors.length}`,
          position: { x: pts[0], y: pts[1] },
          widthMeters: 0.9,
          swingAngleDeg: 90,
        });
      }
    } else if (cat === "WINDOW" && Array.isArray(coords)) {
      const pts = (coords as any).flat(3);
      if (pts.length >= 4) {
        windows.push({
          id: elem.id || elem.global_id || `win_${windows.length}`,
          start: { x: pts[0], y: pts[1] },
          end: { x: pts[2], y: pts[3] },
          thicknessMeters: 0.2,
        });
      }
    } else if (cat === "COLUMN" && Array.isArray(coords)) {
      const pts = (coords as any).flat(3);
      if (pts.length >= 2) {
        columns.push({
          id: elem.id || elem.global_id || `col_${columns.length}`,
          position: { x: pts[0], y: pts[1] },
          widthMeters: 0.6,
          heightMeters: 0.6,
        });
      }
    }
  });

  return {
    id: report.floor_plan_name || "uploaded_fp",
    name: report.floor_plan_name || "Uploaded Floor Plan",
    boundary: boundaryPts.length > 0 ? boundaryPts : [
      { x: 0, y: 0 },
      { x: 20, y: 0 },
      { x: 20, y: 15 },
      { x: 0, y: 15 },
    ],
    walls,
    doors,
    windows,
    columns,
    furniture,
  };
}
