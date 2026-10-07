/**
 * TypeScript contracts for Object Transformation (Task 5.4).
 * Handles move, rotation, and resize operations in world metric units.
 */

import { Point2D } from "../canvas/canvasTypes";

export const MIN_FURNITURE_DIMENSION_METERS = 0.1; // Minimum 0.10m (10 cm) to prevent negative/zero sizes

export type TransformMode = "idle" | "dragging" | "rotating" | "resizing";

export interface TransformChange {
  objectId: string;
  newPosition?: Point2D;
  newRotationDeg?: number;
  newWidthMeters?: number;
  newDepthMeters?: number;
}
