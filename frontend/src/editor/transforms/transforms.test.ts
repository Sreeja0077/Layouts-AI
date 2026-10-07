/**
 * Unit tests for Object Transformation Manager (Task 5.4).
 * Tests position update, angle normalization, minimum dimension safety, locked object protection, and immutability.
 */

import { applyTransform, normalizeAngleDeg } from "./transformManager";
import { FloorPlanRenderModel } from "../renderer/renderTypes";

export function runTransformTests(): boolean {
  let passed = true;

  const model: FloorPlanRenderModel = {
    id: "fp1",
    boundary: [],
    walls: [],
    doors: [],
    windows: [],
    columns: [],
    furniture: [
      { id: "f1", catalogItemId: "desk1", itemType: "DESK", position: { x: 3.0, y: 4.0 }, widthMeters: 1.8, depthMeters: 0.9, rotationDeg: 0, isLocked: false },
      { id: "f_locked", catalogItemId: "cab1", itemType: "CABINET", position: { x: 8.0, y: 2.0 }, widthMeters: 1.0, depthMeters: 0.5, rotationDeg: 0, isLocked: true },
    ],
  };

  const originalJson = JSON.stringify(model);

  // Test 1: Move object
  let updated = applyTransform(model, { objectId: "f1", newPosition: { x: 4.5, y: 5.0 } });
  if (updated.furniture[0].position.x !== 4.5 || updated.furniture[0].position.y !== 5.0) {
    console.error("Transform Test 1 (Move) Failed", updated);
    passed = false;
  }

  // Test 2: Angle normalization
  if (normalizeAngleDeg(370) !== 10 || normalizeAngleDeg(-30) !== 330) {
    console.error("Transform Test 2 (Angle Normalization) Failed");
    passed = false;
  }

  // Test 3: Rotate object
  updated = applyTransform(model, { objectId: "f1", newRotationDeg: 90 });
  if (updated.furniture[0].rotationDeg !== 90) {
    console.error("Transform Test 3 (Rotate) Failed", updated);
    passed = false;
  }

  // Test 4: Minimum dimension clamp (negative size rejected -> clamped to 0.10m)
  updated = applyTransform(model, { objectId: "f1", newWidthMeters: -0.5, newDepthMeters: 0.05 });
  if (updated.furniture[0].widthMeters !== 0.1 || updated.furniture[0].depthMeters !== 0.1) {
    console.error("Transform Test 4 (Min Dimension Clamp) Failed", updated);
    passed = false;
  }

  // Test 5: Locked object protection (should NOT be transformed)
  updated = applyTransform(model, { objectId: "f_locked", newPosition: { x: 10, y: 10 }, newRotationDeg: 180 });
  if (updated.furniture[1].position.x !== 8.0 || updated.furniture[1].rotationDeg !== 0) {
    console.error("Transform Test 5 (Locked Protection) Failed", updated);
    passed = false;
  }

  // Test 6: Input model immutability
  if (JSON.stringify(model) !== originalJson) {
    console.error("Transform Test 6 (Immutability) Failed - source model mutated!");
    passed = false;
  }

  return passed;
}
