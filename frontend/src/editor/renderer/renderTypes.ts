/**
 * Renderer-neutral data models for Layouts AI 2D Editor.
 * Represents architectural render entities in world metric coordinates (meters, degrees).
 * CRITICAL: Zero Konva, React-Konva, or canvas DOM dependencies.
 *
 * Supports both:
 * - Legacy simplified primitives (line-segment walls, point-based doors)
 * - Full IFC polygon geometry for imported BIM elements
 */

export interface RenderPoint {
  x: number;
  y: number;
}

/** A closed polygon ring (exterior or hole) */
export type PolygonRing = RenderPoint[];

/** Full polygon geometry preserving holes */
export interface RenderPolygon {
  /** Exterior ring */
  exterior: PolygonRing;
  /** Interior holes (if any) */
  holes?: PolygonRing[];
}

/**
 * Actual 2D footprint geometry from IFC.
 * Can be a single polygon or multiple disconnected polygons (MultiPolygon).
 */
export interface RenderGeometry {
  /** Individual polygon components */
  polygons: RenderPolygon[];
}

export interface RenderWall {
  id: string;
  storeyName?: string;
  storeyElevationMeters?: number;
  /** Legacy: wall as line segment */
  start?: RenderPoint;
  end?: RenderPoint;
  thicknessMeters: number;
  isExterior?: boolean;
  /** Full polygon geometry from IFC (preferred for imported walls) */
  geometry?: RenderGeometry;
}

export interface RenderDoor {
  id: string;
  storeyName?: string;
  storeyElevationMeters?: number;
  position: RenderPoint;
  widthMeters: number;
  rotationDeg?: number;
  swingAngleDeg?: number;
  swingDirection?: "INSIDE_LEFT" | "INSIDE_RIGHT" | "OUTSIDE_LEFT" | "OUTSIDE_RIGHT";
  /** Full polygon geometry from IFC (preferred for imported doors) */
  geometry?: RenderGeometry;
}

export interface RenderWindow {
  id: string;
  storeyName?: string;
  storeyElevationMeters?: number;
  /** Legacy: window as line segment */
  start?: RenderPoint;
  end?: RenderPoint;
  thicknessMeters?: number;
  /** Full polygon geometry from IFC (preferred for imported windows) */
  geometry?: RenderGeometry;
}

export interface RenderColumn {
  id: string;
  storeyName?: string;
  storeyElevationMeters?: number;
  position: RenderPoint;
  widthMeters: number;
  heightMeters: number;
  shape?: "RECTANGULAR" | "CIRCULAR";
  /** Full polygon geometry from IFC (preferred for imported columns) */
  geometry?: RenderGeometry;
}

export interface RenderSpace {
  id: string;
  storeyName?: string;
  storeyElevationMeters?: number;
  name?: string;
  /** Full polygon geometry from IFC */
  geometry: RenderGeometry;
}

export interface RenderFurniture {
  id: string;
  storeyName?: string;
  storeyElevationMeters?: number;
  catalogItemId?: string;
  itemType: string;
  subtype?: string;
  category?: string;
  sourceIfcType?: string;
  name?: string;
  position: RenderPoint;
  widthMeters: number;
  depthMeters: number;
  rotationDeg: number;
  isLocked?: boolean;
  isImported?: boolean;
  geometry?: RenderGeometry;
  properties?: Record<string, any>;
}

/** Complete renderer-neutral architectural floor plan render model */
export interface FloorPlanRenderModel {
  id: string;
  name?: string;
  boundary: RenderPoint[];
  walls: RenderWall[];
  doors: RenderDoor[];
  windows: RenderWindow[];
  columns: RenderColumn[];
  spaces: RenderSpace[];
  furniture: RenderFurniture[];
  /** World-space origin used for coordinate normalization */
  worldOrigin?: RenderPoint;
  /** Active IFC building storey represented by this render model */
  activeStorey?: string;
  /** Available IFC building storeys in display order */
  availableStoreys?: string[];
}
