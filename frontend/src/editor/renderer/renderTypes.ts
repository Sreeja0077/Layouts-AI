/**
 * Renderer-neutral data models for Layouts AI 2D Editor (Task 5.3).
 * Represents architectural render entities in world metric coordinates (meters, degrees).
 * CRITICAL: Zero Konva, React-Konva, or canvas DOM dependencies.
 */

export interface RenderPoint {
  x: number;
  y: number;
}

export interface RenderWall {
  id: string;
  start: RenderPoint;
  end: RenderPoint;
  thicknessMeters: number;
  isExterior?: boolean;
}

export interface RenderDoor {
  id: string;
  position: RenderPoint;
  widthMeters: number;
  rotationDeg?: number;
  swingAngleDeg?: number;
  swingDirection?: "INSIDE_LEFT" | "INSIDE_RIGHT" | "OUTSIDE_LEFT" | "OUTSIDE_RIGHT";
}

export interface RenderWindow {
  id: string;
  start: RenderPoint;
  end: RenderPoint;
  thicknessMeters?: number;
}

export interface RenderColumn {
  id: string;
  position: RenderPoint;
  widthMeters: number;
  heightMeters: number;
  shape?: "RECTANGULAR" | "CIRCULAR";
}

export interface RenderFurniture {
  id: string;
  catalogItemId: string;
  itemType: string;
  position: RenderPoint;
  widthMeters: number;
  depthMeters: number;
  rotationDeg: number;
  isLocked?: boolean;
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
  furniture: RenderFurniture[];
}
