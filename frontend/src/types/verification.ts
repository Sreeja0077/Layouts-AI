export type VerificationStatus = "PENDING" | "VERIFIED" | "REJECTED";

export interface GeometryAnomalyWarning {
  warning_id: string;
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
  element_type?: string;
  subtype?: string;
  name?: string;
  coordinates: number[][][] | number[][][][] | number[][];
  is_closed?: boolean;
  storey_id?: string | null;
  storey_name?: string | null;
  storey_elevation_m?: number | null;
  properties?: Record<string, any>;
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
  available_storeys?: Array<{
    name: string;
    storey_id?: string | null;
    elevation_m?: number | null;
    element_count?: number;
    wall_count?: number;
    door_count?: number;
    window_count?: number;
    column_count?: number;
    space_count?: number;
    furniture_count?: number;
  }>;
  recommended_storey?: string | null;
  warnings: GeometryAnomalyWarning[];
  reviewer_user_id?: string | null;
  verified_at?: string | null;
  rejection_reason?: string | null;
}
