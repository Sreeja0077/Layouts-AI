/**
 * TypeScript contracts and types for Konva 2D Architectural Canvas (Task 5.2 & Task 5.3).
 * Establishes viewport models, coordinate structures, and canvas props.
 */

import { FloorPlanRenderModel } from "../renderer/renderTypes";

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

/** Legacy alias for backward compatibility */
export type DemoRenderModel = FloorPlanRenderModel;

/** Props for the top-level LayoutCanvas component */
export interface LayoutCanvasProps {
  width?: number;
  height?: number;
  initialScale?: number;
  showGrid?: boolean;
  renderModel?: FloorPlanRenderModel;
  demoModel?: FloorPlanRenderModel;
  className?: string;
  onSwitchFloorPlan?: (projectId: string, floorPlanId: string) => void;
  onGoToUpload?: () => void;
  availableFloorPlans?: Array<{ id: string; name: string }>;
  activeFloorPlanId?: string;
}
