/**
 * Pure, deterministic viewport coordinate transformation helpers (Task 5.2).
 * Converts between world metric coordinates (meters) and screen canvas coordinates (pixels).
 * Pure functions: Zero side-effects, fully unit-testable.
 */

import { Point2D, Viewport } from "./canvasTypes";

export const DEFAULT_MIN_SCALE = 5;   // 5 pixels per meter (zoomed far out)
export const DEFAULT_MAX_SCALE = 500; // 500 pixels per meter (zoomed far in)
export const DEFAULT_INITIAL_SCALE = 40; // 40 pixels per meter (default 1m = 40px)

/**
 * Transforms a world coordinate (meters) to a screen canvas coordinate (pixels).
 */
export function worldToScreen(worldPt: Point2D, viewport: Viewport): Point2D {
  return {
    x: worldPt.x * viewport.scale + viewport.x,
    y: worldPt.y * viewport.scale + viewport.y,
  };
}

/**
 * Transforms a screen canvas coordinate (pixels) to a world coordinate (meters).
 */
export function screenToWorld(screenPt: Point2D, viewport: Viewport): Point2D {
  if (viewport.scale <= 0) {
    return { x: 0, y: 0 };
  }
  return {
    x: (screenPt.x - viewport.x) / viewport.scale,
    y: (screenPt.y - viewport.y) / viewport.scale,
  };
}

/**
 * Clamps scale value within bounded min and max limits.
 */
export function clampScale(
  scale: number,
  minScale = DEFAULT_MIN_SCALE,
  maxScale = DEFAULT_MAX_SCALE
): number {
  return Math.min(Math.max(scale, minScale), maxScale);
}

/**
 * Zooms the viewport centered around a specific screen pointer location.
 * Ensures the world position directly beneath pointerScreenPt remains fixed/anchored under the cursor.
 */
export function zoomAtPoint(
  pointerScreenPt: Point2D,
  zoomFactor: number,
  currentViewport: Viewport,
  minScale = DEFAULT_MIN_SCALE,
  maxScale = DEFAULT_MAX_SCALE
): Viewport {
  const targetScale = currentViewport.scale * zoomFactor;
  const newScale = clampScale(targetScale, minScale, maxScale);

  if (newScale === currentViewport.scale) {
    return currentViewport;
  }

  // Determine the world point directly under the pointer before zooming
  const worldPtUnderPointer = screenToWorld(pointerScreenPt, currentViewport);

  // Calculate new screen offset so the world point remains at pointerScreenPt
  const newX = pointerScreenPt.x - worldPtUnderPointer.x * newScale;
  const newY = pointerScreenPt.y - worldPtUnderPointer.y * newScale;

  return {
    scale: newScale,
    x: newX,
    y: newY,
  };
}

/**
 * Creates default initial viewport centered within container dimensions.
 */
export function createInitialViewport(
  containerWidth: number,
  containerHeight: number,
  scale = DEFAULT_INITIAL_SCALE
): Viewport {
  return {
    scale,
    x: containerWidth / 4,
    y: containerHeight / 4,
  };
}
