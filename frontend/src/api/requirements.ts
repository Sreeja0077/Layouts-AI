/**
 * Requirement AI & Clarification API Client (Phase 8).
 * Facilitates natural-language requirement submission and clarification answers.
 */

const API_BASE = "/api/v1";

export interface ClarificationQuestion {
  question_id: string;
  slot: string;
  question_text: string;
  suggested_options: string[];
  default_fallback_value?: string | null;
}

export interface RequirementItemPayload {
  id: string;
  raw_phrase: string;
  semantic_type?: string | null;
  resolved_catalog_item_id?: string | null;
  resolution_method?: string | null;
  confidence: number;
  quantity: number;
  slot_tags: string[];
  dimensions_override?: Record<string, number> | null;
}

export interface SpatialPreferencePayload {
  target_zone: string;
  item_ids_or_tags: string[];
  preference_type: string;
  importance: string;
}

export interface RequirementSetPayload {
  id: string;
  project_id: string;
  floor_plan_id: string;
  room_id?: string | null;
  status: "DRAFT" | "NORMALIZED" | "CLARIFICATION_REQUIRED" | "FINALIZED";
  items: RequirementItemPayload[];
  preferences: SpatialPreferencePayload[];
  target_density_seats?: number | null;
  target_circulation_ratio: number;
  notes?: string | null;
}

export interface RequirementAnalysisResponse {
  requirement_set_id: string;
  status: "DRAFT" | "NORMALIZED" | "CLARIFICATION_REQUIRED" | "FINALIZED";
  needs_clarification: boolean;
  questions: ClarificationQuestion[];
  reasoning: string;
  confidence: number;
  requirement_set: RequirementSetPayload;
}

export interface SubmitRequirementRequest {
  raw_text: string;
  project_id?: string;
  floor_plan_id?: string;
  region_id?: string;
}

export async function submitRequirement(
  request: SubmitRequirementRequest
): Promise<RequirementAnalysisResponse> {
  const resp = await fetch(`${API_BASE}/requirements/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to submit requirement (${resp.status})`);
  }

  return resp.json();
}

export async function clarifyRequirement(
  requirementSetId: string,
  answer: string,
  questionId?: string
): Promise<RequirementAnalysisResponse> {
  const resp = await fetch(`${API_BASE}/requirements/${requirementSetId}/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer, question_id: questionId }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to clarify requirement (${resp.status})`);
  }

  return resp.json();
}

export async function getRequirement(
  requirementSetId: string
): Promise<RequirementAnalysisResponse> {
  const resp = await fetch(`${API_BASE}/requirements/${requirementSetId}`);

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to get requirement (${resp.status})`);
  }

  return resp.json();
}
