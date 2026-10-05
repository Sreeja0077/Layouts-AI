/**
 * Unit tests for pure viewport helper functions (Task 5.2).
 * Verifies round-trip worldToScreen / screenToWorld coordinate transformations and pointer-anchored zooming.
 */

import {
  worldToScreen,
  screenToWorld,
  clampScale,
  zoomAtPoint,
} from "./viewport";
import { Viewport } from "./canvasTypes";

export function runViewportTests(): boolean {
  let passed = true;

  const vp: Viewport = { scale: 50, x: 100, y: 200 };

  // Test 1: worldToScreen
  const screenPt = worldToScreen({ x: 2, y: 3 }, vp);
  if (screenPt.x !== 200 || screenPt.y !== 350) {
    console.error("worldToScreen test failed", screenPt);
    passed = false;
  }

  // Test 2: screenToWorld round-trip
  const worldPt = screenToWorld(screenPt, vp);
  if (Math.abs(worldPt.x - 2) > 0.0001 || Math.abs(worldPt.y - 3) > 0.0001) {
    console.error("screenToWorld round-trip test failed", worldPt);
    passed = false;
  }

  // Test 3: clampScale
  if (clampScale(2, 5, 500) !== 5 || clampScale(600, 5, 500) !== 500 || clampScale(50, 5, 500) !== 50) {
    console.error("clampScale test failed");
    passed = false;
  }

  // Test 4: zoomAtPoint anchors cursor position
  const cursor = { x: 300, y: 400 };
  const worldPtBefore = screenToWorld(cursor, vp);
  const newVp = zoomAtPoint(cursor, 1.5, vp);
  const worldPtAfter = screenToWorld(cursor, newVp);

  if (Math.abs(worldPtBefore.x - worldPtAfter.x) > 0.0001 || Math.abs(worldPtBefore.y - worldPtAfter.y) > 0.0001) {
    console.error("zoomAtPoint anchored cursor test failed", worldPtBefore, worldPtAfter);
    passed = false;
  }

  return passed;
}
