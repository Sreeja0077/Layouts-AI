/**
 * Pure Freehand Stroke Manager for 2D Architectural Editor (Task 6.1).
 * Manages stroke creation, point sampling/appending, completion, and cancellation.
 * Operates purely on screen-space points with zero backend or Shapely dependencies.
 */

import { Point2D } from "../canvas/canvasTypes";
import { FreehandStroke } from "./freehandTypes";

/** Minimum pixel distance between consecutive recorded stroke points to avoid redundant samples */
export const DEFAULT_SAMPLE_MIN_DIST_PX = 3;

/**
 * Calculates Euclidean distance between two 2D points.
 */
export function calculateDistance(p1: Point2D, p2: Point2D): number {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Initializes a new freehand stroke starting at the given screen-space point.
 */
export function startStroke(startPt: Point2D): FreehandStroke {
  return {
    id: `stroke_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
    points: [{ x: Number(startPt.x.toFixed(1)), y: Number(startPt.y.toFixed(1)) }],
    isDrawing: true,
    isClosed: false,
    createdAt: Date.now(),
  };
}

/**
 * Appends a new point to the stroke if distance from the last point exceeds minDistancePx.
 * Returns a new immutable FreehandStroke object.
 */
export function appendPointToStroke(
  stroke: Readonly<FreehandStroke>,
  pt: Point2D,
  minDistancePx = DEFAULT_SAMPLE_MIN_DIST_PX
): FreehandStroke {
  if (!stroke.isDrawing || stroke.points.length === 0) return stroke;

  const lastPt = stroke.points[stroke.points.length - 1];
  const dist = calculateDistance(lastPt, pt);

  if (dist < minDistancePx) {
    return stroke;
  }

  const newPt = { x: Number(pt.x.toFixed(1)), y: Number(pt.y.toFixed(1)) };
  return {
    ...stroke,
    points: [...stroke.points, newPt],
  };
}

/**
 * Completes an active drawing stroke. Marks isDrawing = false and isClosed = true if valid.
 */
export function completeStroke(stroke: Readonly<FreehandStroke>): FreehandStroke {
  if (stroke.points.length < 3) {
    // Insufficient points for a valid region -> cancel stroke
    return {
      ...stroke,
      points: [],
      isDrawing: false,
      isClosed: false,
    };
  }

  return {
    ...stroke,
    isDrawing: false,
    isClosed: true,
  };
}

/**
 * Cancels current stroke.
 */
export function cancelStroke(): null {
  return null;
}
