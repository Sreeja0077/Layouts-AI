/**
 * Pure Snapping Assistance Engine for 2D Architectural Editor (Task 5.4).
 * Computes grid snapping (0.25m step) and object alignment snapping in world metric units.
 * Deterministic priority: 1) Alignment to nearby objects/walls, 2) Grid snapping.
 */

import { Point2D } from "../canvas/canvasTypes";
import { FloorPlanRenderModel, RenderFurniture, RenderWall } from "../renderer/renderTypes";
import {
  DEFAULT_GRID_SNAP_STEP_METERS,
  DEFAULT_SNAP_TOLERANCE_METERS,
  SnapGuideLine,
  SnapResult,
} from "./snappingTypes";

/**
 * Snaps a single value to the nearest grid step if within tolerance.
 */
export function snapValueToGrid(
  val: number,
  step = DEFAULT_GRID_SNAP_STEP_METERS,
  tolerance = DEFAULT_SNAP_TOLERANCE_METERS
): { snapped: number; isSnapped: boolean } {
  const rounded = Math.round(val / step) * step;
  const diff = Math.abs(val - rounded);
  if (diff <= tolerance) {
    return { snapped: Number(rounded.toFixed(3)), isSnapped: true };
  }
  return { snapped: val, isSnapped: false };
}

/**
 * Snaps a 2D world coordinate point to the drafting grid.
 */
export function snapPointToGrid(
  pt: Point2D,
  step = DEFAULT_GRID_SNAP_STEP_METERS,
  tolerance = DEFAULT_SNAP_TOLERANCE_METERS
): Point2D {
  return {
    x: snapValueToGrid(pt.x, step, tolerance).snapped,
    y: snapValueToGrid(pt.y, step, tolerance).snapped,
  };
}

/**
 * Calculates complete snapping result including alignment snapping, grid snapping, and visual guide lines.
 */
export function calculateSnap(
  targetPos: Point2D,
  targetId: string | null,
  model?: FloorPlanRenderModel,
  gridStep = DEFAULT_GRID_SNAP_STEP_METERS,
  tolerance = DEFAULT_SNAP_TOLERANCE_METERS
): SnapResult {
  let finalX = targetPos.x;
  let finalY = targetPos.y;
  let isSnappedX = false;
  let isSnappedY = false;
  const guides: SnapGuideLine[] = [];

  if (!model) {
    const gridSnap = snapPointToGrid(targetPos, gridStep, tolerance);
    return {
      snappedPosition: gridSnap,
      isSnappedX: gridSnap.x !== targetPos.x,
      isSnappedY: gridSnap.y !== targetPos.y,
      activeGuides: [],
    };
  }

  // Collect alignment candidates (other furniture centers & wall endpoints)
  const candidateX: { val: number; source: string }[] = [];
  const candidateY: { val: number; source: string }[] = [];

  for (const furn of model.furniture) {
    if (furn.id === targetId) continue;
    candidateX.push({ val: furn.position.x, source: furn.id });
    candidateY.push({ val: furn.position.y, source: furn.id });
  }

  for (const wall of model.walls) {
    if (wall.start && wall.end) {
      candidateX.push({ val: wall.start.x, source: wall.id });
      candidateX.push({ val: wall.end.x, source: wall.id });
      candidateY.push({ val: wall.start.y, source: wall.id });
      candidateY.push({ val: wall.end.y, source: wall.id });
    }
  }

  // 1. Try Alignment Snapping for X
  let bestXDiff = tolerance;
  for (const cand of candidateX) {
    const diff = Math.abs(targetPos.x - cand.val);
    if (diff <= bestXDiff) {
      bestXDiff = diff;
      finalX = cand.val;
      isSnappedX = true;
      guides.push({
        id: `guide-v-${cand.source}`,
        type: "VERTICAL",
        positionMeters: cand.val,
        startMeters: { x: cand.val, y: targetPos.y - 5 },
        endMeters: { x: cand.val, y: targetPos.y + 5 },
      });
    }
  }

  // Fallback to Grid Snapping for X if no object alignment found
  if (!isSnappedX) {
    const snapX = snapValueToGrid(targetPos.x, gridStep, tolerance);
    if (snapX.isSnapped) {
      finalX = snapX.snapped;
      isSnappedX = true;
    }
  }

  // 2. Try Alignment Snapping for Y
  let bestYDiff = tolerance;
  for (const cand of candidateY) {
    const diff = Math.abs(targetPos.y - cand.val);
    if (diff <= bestYDiff) {
      bestYDiff = diff;
      finalY = cand.val;
      isSnappedY = true;
      guides.push({
        id: `guide-h-${cand.source}`,
        type: "HORIZONTAL",
        positionMeters: cand.val,
        startMeters: { x: targetPos.x - 5, y: cand.val },
        endMeters: { x: targetPos.x + 5, y: cand.val },
      });
    }
  }

  // Fallback to Grid Snapping for Y if no object alignment found
  if (!isSnappedY) {
    const snapY = snapValueToGrid(targetPos.y, gridStep, tolerance);
    if (snapY.isSnapped) {
      finalY = snapY.snapped;
      isSnappedY = true;
    }
  }

  return {
    snappedPosition: { x: Number(finalX.toFixed(3)), y: Number(finalY.toFixed(3)) },
    isSnappedX,
    isSnappedY,
    activeGuides: guides,
  };
}
