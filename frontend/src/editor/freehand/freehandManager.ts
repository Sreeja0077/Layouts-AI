/**
 * Pure Freehand Stroke & Region Preview Manager for 2D Architectural Editor (Task 6.1 & 6.2).
 * Manages stroke creation, point sampling/appending, screen-to-world conversion,
 * Shoelace area, perimeter, centroid, RDP simplification, and RegionPreview computation.
 */

import { Point2D, Viewport } from "../canvas/canvasTypes";
import { screenToWorld } from "../canvas/viewport";
import { FreehandStroke, RegionPreview } from "./freehandTypes";

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

/**
 * Converts screen-space stroke points into world metric points in meters using active viewport.
 */
export function screenStrokeToWorld(
  stroke: Readonly<FreehandStroke>,
  viewport: Viewport
): Point2D[] {
  return stroke.points.map((pt) => {
    const world = screenToWorld(pt, viewport);
    return {
      x: Number(world.x.toFixed(3)),
      y: Number(world.y.toFixed(3)),
    };
  });
}

/**
 * Calculates enclosed polygon area in square meters (m²) using the Shoelace formula.
 */
export function calculatePolygonAreaSqMeters(worldPoints: Point2D[]): number {
  const n = worldPoints.length;
  if (n < 3) return 0;

  let areaSum = 0;
  for (let i = 0; i < n; i++) {
    const curr = worldPoints[i];
    const next = worldPoints[(i + 1) % n];
    areaSum += curr.x * next.y - next.x * curr.y;
  }

  const area = Math.abs(areaSum) / 2.0;
  return Number(area.toFixed(2));
}

/**
 * Calculates total boundary perimeter length in meters (m), including closing segment.
 */
export function calculatePolygonPerimeterMeters(worldPoints: Point2D[]): number {
  const n = worldPoints.length;
  if (n < 2) return 0;

  let perimeter = 0;
  for (let i = 0; i < n; i++) {
    const curr = worldPoints[i];
    const next = worldPoints[(i + 1) % n];
    perimeter += calculateDistance(curr, next);
  }

  return Number(perimeter.toFixed(2));
}

/**
 * Calculates area-weighted polygon centroid in world meters (x, y).
 * Returns null for degenerate or near-zero area shapes.
 */
export function calculatePolygonCentroid(worldPoints: Point2D[]): Point2D | null {
  const n = worldPoints.length;
  if (n < 3) return null;

  let signedAreaSum = 0;
  let cxSum = 0;
  let cySum = 0;

  for (let i = 0; i < n; i++) {
    const curr = worldPoints[i];
    const next = worldPoints[(i + 1) % n];
    const cross = curr.x * next.y - next.x * curr.y;
    signedAreaSum += cross;
    cxSum += (curr.x + next.x) * cross;
    cySum += (curr.y + next.y) * cross;
  }

  const signedArea = signedAreaSum / 2.0;
  if (Math.abs(signedArea) < 0.0001) {
    // Degenerate zero-area polygon -> fallback to arithmetic mean of points
    let sumX = 0;
    let sumY = 0;
    for (const p of worldPoints) {
      sumX += p.x;
      sumY += p.y;
    }
    return {
      x: Number((sumX / n).toFixed(2)),
      y: Number((sumY / n).toFixed(2)),
    };
  }

  const factor = 1.0 / (6.0 * signedArea);
  const cx = cxSum * factor;
  const cy = cySum * factor;

  if (!isFinite(cx) || !isFinite(cy)) return null;

  return {
    x: Number(cx.toFixed(2)),
    y: Number(cy.toFixed(2)),
  };
}

/**
 * Ramer-Douglas-Peucker (RDP) algorithm for conservative world point simplification.
 */
export function simplifyWorldPoints(
  points: Point2D[],
  toleranceMeters = 0.05
): Point2D[] {
  if (points.length <= 2) return points;

  const perpendicularDistance = (p: Point2D, p1: Point2D, p2: Point2D): number => {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const lineLenSq = dx * dx + dy * dy;
    if (lineLenSq === 0) return calculateDistance(p, p1);

    const t = Math.max(0, Math.min(1, ((p.x - p1.x) * dx + (p.y - p1.y) * dy) / lineLenSq));
    const projX = p1.x + t * dx;
    const projY = p1.y + t * dy;
    return calculateDistance(p, { x: projX, y: projY });
  };

  const rdp = (pts: Point2D[], tol: number): Point2D[] => {
    if (pts.length <= 2) return pts;
    let maxDist = 0;
    let index = 0;
    const first = pts[0];
    const last = pts[pts.length - 1];

    for (let i = 1; i < pts.length - 1; i++) {
      const dist = perpendicularDistance(pts[i], first, last);
      if (dist > maxDist) {
        maxDist = dist;
        index = i;
      }
    }

    if (maxDist > tol) {
      const left = rdp(pts.slice(0, index + 1), tol);
      const right = rdp(pts.slice(index), tol);
      return [...left.slice(0, left.length - 1), ...right];
    } else {
      return [first, last];
    }
  };

  return rdp(points, toleranceMeters);
}

/**
 * Computes complete RegionPreview object from a FreehandStroke and active Viewport.
 */
export function computeRegionPreview(
  stroke: FreehandStroke | null,
  viewport: Viewport
): RegionPreview | null {
  if (!stroke || stroke.points.length === 0) return null;

  const rawWorldPoints = screenStrokeToWorld(stroke, viewport);
  const worldPoints = simplifyWorldPoints(rawWorldPoints, 0.05);

  const areaSqMeters = calculatePolygonAreaSqMeters(worldPoints);
  const perimeterMeters = calculatePolygonPerimeterMeters(worldPoints);
  const centroid = calculatePolygonCentroid(worldPoints);
  const isValid = worldPoints.length >= 3 && areaSqMeters > 0.0001;

  return {
    strokeId: stroke.id,
    worldPoints,
    areaSqMeters,
    perimeterMeters,
    centroid,
    isClosed: stroke.isClosed,
    isValid,
  };
}
