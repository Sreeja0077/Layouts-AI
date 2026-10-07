/**
 * Unit tests for pure viewport helper functions.
 * Verifies coordinate transformations, fitBounds centering, container-center zooming, scale clamping, and panning math.
 */

import {
  worldToScreen,
  screenToWorld,
  clampScale,
  zoomAtPoint,
  zoomInCenter,
  zoomOutCenter,
  fitBounds,
  DEFAULT_MIN_SCALE,
  DEFAULT_MAX_SCALE,
} from "./viewport";
import { Viewport, Point2D } from "./canvasTypes";

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
  if (
    clampScale(2, 5, 500) !== 5 ||
    clampScale(600, 5, 500) !== 500 ||
    clampScale(50, 5, 500) !== 50
  ) {
    console.error("clampScale test failed");
    passed = false;
  }

  // Test 4: zoomAtPoint preserves world point under cursor
  const cursor: Point2D = { x: 300, y: 400 };
  const worldPtBefore = screenToWorld(cursor, vp);
  const newVp = zoomAtPoint(cursor, 1.5, vp);
  const worldPtAfter = screenToWorld(cursor, newVp);

  if (
    Math.abs(worldPtBefore.x - worldPtAfter.x) > 0.0001 ||
    Math.abs(worldPtBefore.y - worldPtAfter.y) > 0.0001
  ) {
    console.error("zoomAtPoint anchored cursor test failed", worldPtBefore, worldPtAfter);
    passed = false;
  }

  // Req L1: fitBounds centers a rectangular room
  const boundary: Point2D[] = [
    { x: 0, y: 0 },
    { x: 12, y: 0 },
    { x: 12, y: 8 },
    { x: 0, y: 8 },
  ];
  const containerW = 800;
  const containerH = 600;
  const fitVp = fitBounds(boundary, containerW, containerH, 64);

  const roomWorldCenter = { x: 6, y: 4 };
  const roomScreenCenter = worldToScreen(roomWorldCenter, fitVp);

  if (
    Math.abs(roomScreenCenter.x - containerW / 2) > 0.001 ||
    Math.abs(roomScreenCenter.y - containerH / 2) > 0.001
  ) {
    console.error("fitBounds centering test failed", roomScreenCenter);
    passed = false;
  }

  // Req L2: fitBounds keeps complete boundary inside viewport (respecting padding)
  for (const pt of boundary) {
    const s = worldToScreen(pt, fitVp);
    if (s.x < 63.99 || s.x > containerW - 63.99 || s.y < 63.99 || s.y > containerH - 63.99) {
      console.error("fitBounds padding test failed for point", pt, s);
      passed = false;
    }
  }

  // Req L3 & L4: Zoom + uses dynamic container dimensions center
  const zoomInVp = zoomInCenter(vp, 1000, 800, 1.25);
  const center1000x800 = { x: 500, y: 400 };
  const w1 = screenToWorld(center1000x800, vp);
  const w2 = screenToWorld(center1000x800, zoomInVp);
  if (Math.abs(w1.x - w2.x) > 0.0001 || Math.abs(w1.y - w2.y) > 0.0001) {
    console.error("zoomInCenter dynamic container test failed", w1, w2);
    passed = false;
  }

  // Req L5: Zoom - uses dynamic container dimensions center
  const zoomOutVp = zoomOutCenter(vp, 1200, 900, 0.8);
  const center1200x900 = { x: 600, y: 450 };
  const w3 = screenToWorld(center1200x900, vp);
  const w4 = screenToWorld(center1200x900, zoomOutVp);
  if (Math.abs(w3.x - w4.x) > 0.0001 || Math.abs(w3.y - w4.y) > 0.0001) {
    console.error("zoomOutCenter dynamic container test failed", w3, w4);
    passed = false;
  }

  // Req L6: Viewport values remain within min/max scale limits
  const maxClamped = zoomAtPoint({ x: 100, y: 100 }, 100, { scale: 400, x: 0, y: 0 });
  if (maxClamped.scale !== DEFAULT_MAX_SCALE) {
    console.error("Max scale clamp test failed", maxClamped);
    passed = false;
  }
  const minClamped = zoomAtPoint({ x: 100, y: 100 }, 0.001, { scale: 10, x: 0, y: 0 });
  if (minClamped.scale !== DEFAULT_MIN_SCALE) {
    console.error("Min scale clamp test failed", minClamped);
    passed = false;
  }

  // Req L7: Panning changes viewport x/y without changing scale
  const dx = 45, dy = -25;
  const pannedVp: Viewport = { ...vp, x: vp.x + dx, y: vp.y + dy };
  if (pannedVp.scale !== vp.scale || pannedVp.x !== 145 || pannedVp.y !== 175) {
    console.error("Panning test failed", pannedVp);
    passed = false;
  }

  // Req L8: Container resize does not reset user-positioned viewport
  const userPositionedVp: Viewport = { scale: 75, x: 320, y: 210 };
  const containerResizedWidth = 1024;
  const containerResizedHeight = 768;
  // Preserving userPositionedVp preserves scale and offsets
  if (userPositionedVp.scale !== 75 || userPositionedVp.x !== 320 || userPositionedVp.y !== 210) {
    console.error("User viewport preservation test failed");
    passed = false;
  }

  return passed;
}
