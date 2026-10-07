/**
 * TypeScript contracts and models for Freehand Region Selection (Task 6.1 & Task 6.2).
 * Establishes stroke capture types and world-space RegionPreview geometry contracts.
 */

import { Point2D } from "../canvas/canvasTypes";

export type EditorToolMode = "select" | "pan" | "freehand_region";

export interface FreehandStroke {
  id: string;
  /** Points stored in screen-space canvas stage pixel coordinates */
  points: Point2D[];
  isDrawing: boolean;
  isClosed: boolean;
  createdAt: number;
}

export interface RegionPreview {
  strokeId: string;
  /** Polygon vertices in world metric units (meters) */
  worldPoints: Point2D[];
  /** Total enclosed surface area in square meters (m²) */
  areaSqMeters: number;
  /** Total boundary perimeter length in meters (m) */
  perimeterMeters: number;
  /** Polygon geometric center point in world meters (x, y) */
  centroid: Point2D | null;
  isClosed: boolean;
  /** True if polygon has ≥ 3 points and non-zero area */
  isValid: boolean;
}
