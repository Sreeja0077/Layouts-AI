/**
 * TypeScript contracts and types for Konva 2D Architectural Canvas (Task 5.2).
 * Establishes viewport models, coordinate structures, and temporary demo render schemas.
 */

export interface Point2D {
  x: number;
  y: number;
}

export interface Viewport {
  /** Scale in pixels per meter */
  scale: number;
  /** Screen X offset of world origin (0,0) in pixels */
  x: number;
  /** Screen Y offset of world origin (0,0) in pixels */
  y: number;
}

/** Architectural Wall item representation for canvas rendering */
export interface DemoWall {
  id: string;
  start: Point2D;
  end: Point2D;
  thicknessMeters: number;
}

/** Architectural Door item representation for canvas rendering */
export interface DemoDoor {
  id: string;
  position: Point2D;
  widthMeters: number;
  swingAngleDeg: number;
}

/** Architectural Column obstacle representation for canvas rendering */
export interface DemoColumn {
  id: string;
  position: Point2D;
  widthMeters: number;
  heightMeters: number;
}

/** Temporary typed render model for Task 5.2 visual floor-plan demonstration */
export interface DemoRenderModel {
  roomId: string;
  roomName: string;
  boundaryPolygon: Point2D[];
  walls: DemoWall[];
  doors: DemoDoor[];
  columns: DemoColumn[];
}

/** Props for the top-level LayoutCanvas component */
export interface LayoutCanvasProps {
  width?: number;
  height?: number;
  initialScale?: number;
  showGrid?: boolean;
  demoModel?: DemoRenderModel;
  className?: string;
}
