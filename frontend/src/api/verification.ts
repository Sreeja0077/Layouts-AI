import { GeometryVerificationReport } from "../types/verification";

const API_BASE = "/api/v1";

export async function fetchVerificationReport(
  projectId: string = "proj_101",
  floorPlanId: string = "fp_501"
): Promise<GeometryVerificationReport> {
  const resp = await fetch(
    `${API_BASE}/projects/${projectId}/floor-plans/${floorPlanId}/verification-report`
  );
  if (!resp.ok) {
    throw new Error(`Failed to fetch verification report: ${resp.statusText}`);
  }
  return resp.json();
}

export async function verifyFloorPlan(
  projectId: string = "proj_101",
  floorPlanId: string = "fp_501"
): Promise<GeometryVerificationReport> {
  const resp = await fetch(
    `${API_BASE}/projects/${projectId}/floor-plans/${floorPlanId}/verify`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }
  );
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `Verification failed: ${resp.statusText}`);
  }
  return resp.json();
}

export async function rejectFloorPlan(
  projectId: string = "proj_101",
  floorPlanId: string = "fp_501",
  rejectionReason: string
): Promise<GeometryVerificationReport> {
  const resp = await fetch(
    `${API_BASE}/projects/${projectId}/floor-plans/${floorPlanId}/reject`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rejection_reason: rejectionReason }),
    }
  );
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `Rejection failed: ${resp.statusText}`);
  }
  return resp.json();
}
