/**
 * Pure viewport coordinate transformation helpers for the 2D architectural editor.
 */
import { Point2D, Viewport } from "./canvasTypes";

export const DEFAULT_MIN_SCALE = 5;
export const DEFAULT_MAX_SCALE = 500;
export const DEFAULT_INITIAL_SCALE = 40;

export function worldToScreen(worldPt: Point2D, viewport: Viewport): Point2D {
  return { x: worldPt.x * viewport.scale + viewport.x, y: worldPt.y * viewport.scale + viewport.y };
}

export function screenToWorld(screenPt: Point2D, viewport: Viewport): Point2D {
  if (viewport.scale <= 0) return { x: 0, y: 0 };
  return { x: (screenPt.x - viewport.x) / viewport.scale, y: (screenPt.y - viewport.y) / viewport.scale };
}

export function clampScale(scale: number, minScale = DEFAULT_MIN_SCALE, maxScale = DEFAULT_MAX_SCALE): number {
  return Math.min(Math.max(scale, minScale), maxScale);
}

export function zoomAtPoint(pointerScreenPt: Point2D, zoomFactor: number, currentViewport: Viewport, minScale = DEFAULT_MIN_SCALE, maxScale = DEFAULT_MAX_SCALE): Viewport {
  const newScale = clampScale(currentViewport.scale * zoomFactor, minScale, maxScale);
  if (newScale === currentViewport.scale) return currentViewport;
  const worldPtUnderPointer = screenToWorld(pointerScreenPt, currentViewport);
  return {
    scale: newScale,
    x: pointerScreenPt.x - worldPtUnderPointer.x * newScale,
    y: pointerScreenPt.y - worldPtUnderPointer.y * newScale,
  };
}

export function fitBounds(points: Point2D[], containerWidth: number, containerHeight: number, padding = 64): Viewport {
  if (!points.length || containerWidth <= 0 || containerHeight <= 0) {
    return { scale: DEFAULT_INITIAL_SCALE, x: containerWidth / 2, y: containerHeight / 2 };
  }
  const minX = Math.min(...points.map(p => p.x));
  const maxX = Math.max(...points.map(p => p.x));
  const minY = Math.min(...points.map(p => p.y));
  const maxY = Math.max(...points.map(p => p.y));
  const width = Math.max(maxX - minX, 0.1);
  const height = Math.max(maxY - minY, 0.1);
  const availableWidth = Math.max(containerWidth - padding * 2, 100);
  const availableHeight = Math.max(containerHeight - padding * 2, 100);
  const scale = clampScale(Math.min(availableWidth / width, availableHeight / height));
  return {
    scale,
    x: containerWidth / 2 - ((minX + maxX) / 2) * scale,
    y: containerHeight / 2 - ((minY + maxY) / 2) * scale,
  };
}

export function createInitialViewport(containerWidth: number, containerHeight: number, scale = DEFAULT_INITIAL_SCALE): Viewport {
  return { scale, x: containerWidth / 2, y: containerHeight / 2 };
}

/**
 * Zooms into the canvas centered around the visible container's midpoint.
 */
export function zoomInCenter(
  viewport: Viewport,
  containerWidth: number,
  containerHeight: number,
  zoomFactor = 1.25,
  minScale = DEFAULT_MIN_SCALE,
  maxScale = DEFAULT_MAX_SCALE
): Viewport {
  const center: Point2D = { x: containerWidth / 2, y: containerHeight / 2 };
  return zoomAtPoint(center, zoomFactor, viewport, minScale, maxScale);
}

/**
 * Zooms out of the canvas centered around the visible container's midpoint.
 */
export function zoomOutCenter(
  viewport: Viewport,
  containerWidth: number,
  containerHeight: number,
  zoomFactor = 0.8,
  minScale = DEFAULT_MIN_SCALE,
  maxScale = DEFAULT_MAX_SCALE
): Viewport {
  const center: Point2D = { x: containerWidth / 2, y: containerHeight / 2 };
  return zoomAtPoint(center, zoomFactor, viewport, minScale, maxScale);
}

