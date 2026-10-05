export type VerificationStatus = "PENDING" | "VERIFIED" | "REJECTED";

export interface GeometryAnomalyWarning {
  warning_id: str;
  warning_type: string;
  severity: "WARNING" | "CRITICAL";
  element_id?: string;
  message: string;
}

export interface Geometry2D {
  type: "Polygon" | "MultiPolygon";
  coordinates: number[][][] | number[][][][];
}

export interface ElementGeometry {
  id: string;
  global_id: string;
  category: "WALL" | "DOOR" | "WINDOW" | "COLUMN" | "SPACE" | "FURNITURE" | "GENERIC" | string;
  type: string;
  coordinates: number[][][] | number[][][][] | number[][];
  is_closed?: boolean;
}

export interface GeometryVerificationReport {
  floor_plan_name: string;
  source_type: "IFC" | "DXF" | string;
  is_geometry_valid: boolean;
  verification_status: VerificationStatus;
  total_rooms_count: number;
  total_net_area_sqm: number;
  boundary_polygon: number[][];
  boundary_geometry?: Geometry2D | null;
  elements_summary: Record<string, number>;
  all_elements_geometry: ElementGeometry[];
  warnings: GeometryAnomalyWarning[];
  reviewer_user_id?: string | null;
  verified_at?: string | null;
  rejection_reason?: string | null;
}
