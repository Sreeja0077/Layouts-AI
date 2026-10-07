/**
 * TypeScript contracts and models for Freehand Region Selection (Task 6.1).
 * Captures user stroke points in screen-space canvas stage coordinates.
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
