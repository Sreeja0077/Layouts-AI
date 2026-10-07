/**
 * Unit tests for Snapping Engine (Task 5.4).
 * Tests grid snapping, tolerance limits, alignment snapping, and deterministic output.
 */

import { snapValueToGrid, snapPointToGrid, calculateSnap } from "./snapper";
import { FloorPlanRenderModel } from "../renderer/renderTypes";

export function runSnappingTests(): boolean {
  let passed = true;

  // Test 1: Grid snapping value rounding (3.13m -> 3.25m for 0.25m step)
  const res1 = snapValueToGrid(3.13, 0.25, 0.15);
  if (res1.snapped !== 3.25 || !res1.isSnapped) {
    console.error("Snap Test 1 Failed", res1);
    passed = false;
  }

  // Test 2: Grid snapping rounding down (3.04m -> 3.00m)
  const res2 = snapValueToGrid(3.04, 0.25, 0.15);
  if (res2.snapped !== 3.00 || !res2.isSnapped) {
    console.error("Snap Test 2 Failed", res2);
    passed = false;
  }

  // Test 3: Outside tolerance -> no snap (3.12m with tolerance 0.05m -> stays 3.12m)
  const res3 = snapValueToGrid(3.12, 0.25, 0.05);
  if (res3.snapped !== 3.12 || res3.isSnapped) {
    console.error("Snap Test 3 (Tolerance) Failed", res3);
    passed = false;
  }

  // Test 4: Point snap to grid
  const ptSnap = snapPointToGrid({ x: 3.13, y: 4.07 }, 0.25, 0.15);
  if (ptSnap.x !== 3.25 || ptSnap.y !== 4.00) {
    console.error("Snap Test 4 (Point) Failed", ptSnap);
    passed = false;
  }

  // Test 5: Alignment snapping to nearby furniture center
  const model: FloorPlanRenderModel = {
    id: "fp1",
    boundary: [],
    walls: [],
    doors: [],
    windows: [],
    columns: [],
    furniture: [
      { id: "f1", catalogItemId: "d1", itemType: "DESK", position: { x: 5.0, y: 2.0 }, widthMeters: 1.6, depthMeters: 0.8, rotationDeg: 0 },
    ],
  };

  const alignRes = calculateSnap({ x: 5.03, y: 3.14 }, "f2", model, 0.25, 0.10);
  if (alignRes.snappedPosition.x !== 5.0 || alignRes.activeGuides.length === 0) {
    console.error("Snap Test 5 (Alignment) Failed", alignRes);
    passed = false;
  }

  return passed;
}
