/**
 * Geometry calculation utilities operating in world meters for Layouts AI 2D CAD renderer.
 * CRITICAL: Zero DOM/pixel dependencies. Pure geometric functions.
 */

import { RenderGeometry, RenderPoint } from "./renderTypes";

export function normalizeVector(v: RenderPoint): RenderPoint {
  const len = Math.hypot(v.x, v.y);
  if (len < 1e-9) return { x: 1, y: 0 };
  return { x: v.x / len, y: v.y / len };
}

export function angleFromVector(v: RenderPoint): number {
  return (Math.atan2(v.y, v.x) * 180) / Math.PI;
}

export function rotatePoint(
  p: RenderPoint,
  angleDeg: number,
  center: RenderPoint = { x: 0, y: 0 }
): RenderPoint {
  const rad = (angleDeg * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const dx = p.x - center.x;
  const dy = p.y - center.y;
  return {
    x: center.x + dx * cos - dy * sin,
    y: center.y + dx * sin + dy * cos,
  };
}

export function dot(v1: RenderPoint, v2: RenderPoint): number {
  return v1.x * v2.x + v1.y * v2.y;
}

export function distance(p1: RenderPoint, p2: RenderPoint): number {
  return Math.hypot(p2.x - p1.x, p2.y - p1.y);
}

export function projectPointToLine(
  p: RenderPoint,
  lineStart: RenderPoint,
  lineEnd: RenderPoint
): RenderPoint {
  const dx = lineEnd.x - lineStart.x;
  const dy = lineEnd.y - lineStart.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < 1e-9) return { ...lineStart };

  const t = Math.max(0, Math.min(1, ((p.x - lineStart.x) * dx + (p.y - lineStart.y) * dy) / lenSq));
  return {
    x: lineStart.x + t * dx,
    y: lineStart.y + t * dy,
  };
}

/**
 * Standard Ray-casting algorithm for Point-in-Polygon containment test.
 */
export function pointInPolygon(point: RenderPoint, polygon: RenderPoint[]): boolean {
  if (!polygon || polygon.length < 3) return false;
  let inside = false;
  const x = point.x;
  const y = point.y;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x,
      yi = polygon[i].y;
    const xj = polygon[j].x,
      yj = polygon[j].y;

    const intersect =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi + 1e-12) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

/**
 * Calculate area of closed polygon ring in square meters.
 */
export function calculatePolygonArea(polygon: RenderPoint[]): number {
  if (!polygon || polygon.length < 3) return 0;
  let area = 0;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    area += (polygon[j].x + polygon[i].x) * (polygon[j].y - polygon[i].y);
  }
  return Math.abs(area / 2);
}

/**
 * Extract oriented bounding box (pos, width, depth, rotationDeg) from 2D polygon footprint.
 */
export function extractOrientedBounds(geometry: RenderGeometry): {
  pos: RenderPoint;
  width: number;
  depth: number;
  rotation: number;
} {
  const pts: RenderPoint[] = [];
  for (const poly of geometry.polygons || []) {
    pts.push(...(poly.exterior || []));
  }
  if (pts.length === 0) {
    return { pos: { x: 0, y: 0 }, width: 1.0, depth: 0.2, rotation: 0 };
  }

  const cx = pts.reduce((sum, p) => sum + p.x, 0) / pts.length;
  const cy = pts.reduce((sum, p) => sum + p.y, 0) / pts.length;

  if (pts.length < 3) {
    return { pos: { x: cx, y: cy }, width: 0.9, depth: 0.2, rotation: 0 };
  }

  // Calculate covariance matrix to find principal orientation angle
  let sxx = 0,
    sxy = 0,
    syy = 0;
  for (const p of pts) {
    const dx = p.x - cx;
    const dy = p.y - cy;
    sxx += dx * dx;
    sxy += dx * dy;
    syy += dy * dy;
  }

  let angleRad = 0.5 * Math.atan2(2 * sxy, sxx - syy);
  let rotationDeg = (angleRad * 180) / Math.PI;

  const cosA = Math.cos(-angleRad);
  const sinA = Math.sin(-angleRad);

  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;
  for (const p of pts) {
    const dx = p.x - cx;
    const dy = p.y - cy;
    const rx = dx * cosA - dy * sinA;
    const ry = dx * sinA + dy * cosA;
    if (rx < minX) minX = rx;
    if (rx > maxX) maxX = rx;
    if (ry < minY) minY = ry;
    if (ry > maxY) maxY = ry;
  }

  let width = maxX - minX;
  let depth = maxY - minY;

  // For architectural elements, width is the larger span along host direction
  if (width < depth) {
    const temp = width;
    width = depth;
    depth = temp;
    rotationDeg += 90;
  }

  rotationDeg = ((rotationDeg + 180) % 360) - 180;

  return {
    pos: { x: cx, y: cy },
    width: Math.max(0.1, width),
    depth: Math.max(0.05, depth),
    rotation: rotationDeg,
  };
}

/**
 * Calculates shortest distance from a point to polygon perimeter boundary edges.
 */
export function distanceToPolygonBoundary(p: RenderPoint, polygon: RenderPoint[]): number {
  if (!polygon || polygon.length < 2) return 0;
  let minDist = Infinity;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const proj = projectPointToLine(p, polygon[j], polygon[i]);
    const d = distance(p, proj);
    if (d < minDist) minDist = d;
  }
  return minDist;
}

export interface OptimalRoomLabelResult {
  point: RenderPoint;
  clearRadius: number; // in world meters
}

/**
 * Finds the optimal obstacle-free visible anchor point for a room label strictly inside the room polygon,
 * maximizing the inscribed obstacle-free clear radius from walls and furniture.
 */
export function findOptimalRoomLabelAnchor(
  poly: RenderPoint[],
  furniture: ReadonlyArray<{ position?: RenderPoint }> = [],
  fallbackCentroid: RenderPoint
): OptimalRoomLabelResult {
  if (!poly || poly.length < 3) {
    return { point: fallbackCentroid, clearRadius: 1.0 };
  }

  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;
  for (const pt of poly) {
    minX = Math.min(minX, pt.x);
    maxX = Math.max(maxX, pt.x);
    minY = Math.min(minY, pt.y);
    maxY = Math.max(maxY, pt.y);
  }

  const spanX = maxX - minX;
  const spanY = maxY - minY;
  if (spanX < 0.2 || spanY < 0.2) {
    return { point: fallbackCentroid, clearRadius: 0.5 };
  }

  // Filter furniture items strictly inside this room polygon
  const insideFurn = furniture.filter((f) => {
    if (!f.position) return false;
    return pointInPolygon(f.position, poly);
  });

  // Dense grid sampling across the room bounding box
  const uSteps = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85];
  const vSteps = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.88];

  let bestPoint = fallbackCentroid;
  let maxClearRadius = 0.5;
  let bestScore = -Infinity;

  for (const u of uSteps) {
    for (const v of vSteps) {
      const cand: RenderPoint = {
        x: minX + u * spanX,
        y: minY + v * spanY,
      };

      // 1. Must be strictly inside the room polygon
      if (!pointInPolygon(cand, poly)) continue;

      // 2. Clearance to nearest room perimeter wall
      const dWall = distanceToPolygonBoundary(cand, poly);
      if (dWall < 0.35) continue;

      // 3. Clearance to nearest furniture
      let minDFurn = 5.0;
      for (const f of insideFurn) {
        if (f.position) {
          minDFurn = Math.min(minDFurn, distance(cand, f.position));
        }
      }

      // Inscribed obstacle-free circle radius
      const clearRadius = Math.min(dWall, minDFurn);

      // Score: maximize clear radius, slight bonus for upper half
      const topBonus = v >= 0.55 ? 0.4 : 0.0;
      const score = clearRadius * 3.5 + dWall * 1.0 + topBonus;

      if (score > bestScore) {
        bestScore = score;
        bestPoint = cand;
        maxClearRadius = clearRadius;
      }
    }
  }

  if (bestScore === -Infinity) {
    if (pointInPolygon(fallbackCentroid, poly)) {
      const dWall = distanceToPolygonBoundary(fallbackCentroid, poly);
      return { point: fallbackCentroid, clearRadius: Math.max(0.5, dWall) };
    }
    return { point: fallbackCentroid, clearRadius: 0.5 };
  }

  return { point: bestPoint, clearRadius: maxClearRadius };
}

