/**
 * Object Transformation Manager for 2D Architectural Editor (Task 5.4).
 * Pure transformation functions operating in world metric units (meters, degrees).
 * Enforces locked object safety and minimum dimension bounds.
 */

import { FloorPlanRenderModel, RenderFurniture } from "../renderer/renderTypes";
import { MIN_FURNITURE_DIMENSION_METERS, TransformChange } from "./transformTypes";

/**
 * Normalizes rotation angle into standard [0, 360) degrees range.
 */
export function normalizeAngleDeg(deg: number): number {
  let normalized = deg % 360;
  if (normalized < 0) {
    normalized += 360;
  }
  return Number(normalized.toFixed(1));
}

/**
 * Applies a transformation change to a floor plan render model immutably.
 * Rejects modifications to locked objects (`isLocked === true`) and enforces minimum dimensions.
 */
export function applyTransform(
  model: Readonly<FloorPlanRenderModel>,
  change: TransformChange
): FloorPlanRenderModel {
  if (!change.objectId) return model;

  const targetIdx = model.furniture.findIndex((item) => item.id === change.objectId);
  if (targetIdx === -1) return model;

  const target = model.furniture[targetIdx];

  // Locked safety guard: locked objects cannot be moved, rotated, or resized
  if (target.isLocked) {
    return model;
  }

  // Compute updated parameters with bounds safety
  const updatedFurnitureItem: RenderFurniture = {
    ...target,
    position: change.newPosition
      ? { x: Number(change.newPosition.x.toFixed(3)), y: Number(change.newPosition.y.toFixed(3)) }
      : target.position,
    rotationDeg: change.newRotationDeg !== undefined
      ? normalizeAngleDeg(change.newRotationDeg)
      : target.rotationDeg,
    widthMeters: change.newWidthMeters !== undefined
      ? Number(Math.max(MIN_FURNITURE_DIMENSION_METERS, change.newWidthMeters).toFixed(3))
      : target.widthMeters,
    depthMeters: change.newDepthMeters !== undefined
      ? Number(Math.max(MIN_FURNITURE_DIMENSION_METERS, change.newDepthMeters).toFixed(3))
      : target.depthMeters,
  };

  // Return new immutable FloorPlanRenderModel with updated furniture item
  const newFurniture = [...model.furniture];
  newFurniture[targetIdx] = updatedFurnitureItem;

  return {
    ...model,
    furniture: newFurniture,
  };
}
