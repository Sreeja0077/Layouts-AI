/**
 * TypeScript contracts for Editor Snapping Assistance (Task 5.4).
 * Pure snapping models operating in world metric units (meters).
 */

import { Point2D } from "../canvas/canvasTypes";

export const DEFAULT_GRID_SNAP_STEP_METERS = 0.25; // 0.25m (25 cm) drafting grid step
export const DEFAULT_SNAP_TOLERANCE_METERS = 0.10;  // 0.10m (10 cm) snap activation tolerance

export interface SnapGuideLine {
  id: string;
  type: "VERTICAL" | "HORIZONTAL";
  positionMeters: number;
  startMeters: Point2D;
  endMeters: Point2D;
}

export interface SnapResult {
  snappedPosition: Point2D;
  isSnappedX: boolean;
  isSnappedY: boolean;
  activeGuides: SnapGuideLine[];
}
