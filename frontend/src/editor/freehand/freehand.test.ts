/**
 * Unit tests for Freehand Region Stroke Capture & World Region Preview (Task 6.1 & Task 6.2).
 * Tests stroke lifecycle, screen-to-world transform, Shoelace area, perimeter, centroid,
 * viewport invariance across pan/zoom, and degenerate polygon safety.
 */

import {
  startStroke,
  appendPointToStroke,
  completeStroke,
  cancelStroke,
  calculateDistance,
  screenStrokeToWorld,
  calculatePolygonAreaSqMeters,
  calculatePolygonPerimeterMeters,
  calculatePolygonCentroid,
  computeRegionPreview,
} from "./freehandManager";
import { FreehandStroke } from "./freehandTypes";
import { Viewport, Point2D } from "../canvas/canvasTypes";
import { worldToScreen, screenToWorld } from "../canvas/viewport";

export function runFreehandTests(): boolean {
  let passed = true;

  // --- Task 6.1 Stroke Capture Unit Tests ---
  let activeStroke: FreehandStroke | null = null;
  if (activeStroke !== null) {
    console.error("Freehand Test 1 Failed: Initial stroke not null");
    passed = false;
  }

  activeStroke = startStroke({ x: 100, y: 200 });
  if (
    !activeStroke ||
    activeStroke.points.length !== 1 ||
    activeStroke.points[0].x !== 100 ||
    !activeStroke.isDrawing
  ) {
    console.error("Freehand Test 2 Failed: startStroke incorrect", activeStroke);
    passed = false;
  }

  activeStroke = appendPointToStroke(activeStroke, { x: 110, y: 200 }, 3);
  activeStroke = appendPointToStroke(activeStroke, { x: 110, y: 250 }, 3);
  const completed = completeStroke(activeStroke);
  if (!completed || completed.isClosed !== true) {
    console.error("Freehand Test 3 Failed: completeStroke incorrect", completed);
    passed = false;
  }

  // --- Task 6.2 Screen-to-World & Geometry Metrics Unit Tests ---
  const vp: Viewport = { scale: 50, x: 100, y: 200 };

  // TEST 1: screenToWorld conversion: known viewport + known screen point -> expected world point
  const knownScreenPt: Point2D = { x: 250, y: 400 }; // (250-100)/50 = 3, (400-200)/50 = 4
  const expectedWorldPt = screenToWorld(knownScreenPt, vp);
  if (expectedWorldPt.x !== 3.0 || expectedWorldPt.y !== 4.0) {
    console.error("Task 6.2 TEST 1 Failed: screenToWorld math", expectedWorldPt);
    passed = false;
  }

  // TEST 2: worldToScreen + screenToWorld round trip
  const originalWorldPt: Point2D = { x: 7.5, y: 12.25 };
  const sPt = worldToScreen(originalWorldPt, vp);
  const roundTripWorldPt = screenToWorld(sPt, vp);
  if (
    Math.abs(originalWorldPt.x - roundTripWorldPt.x) > 0.0001 ||
    Math.abs(originalWorldPt.y - roundTripWorldPt.y) > 0.0001
  ) {
    console.error("Task 6.2 TEST 2 Failed: Round trip world conversion", roundTripWorldPt);
    passed = false;
  }

  // TEST 3: 4 x 3 rectangle: area = 12 m²
  const rectWorldPts: Point2D[] = [
    { x: 0, y: 0 },
    { x: 4, y: 0 },
    { x: 4, y: 3 },
    { x: 0, y: 3 },
  ];
  const rectArea = calculatePolygonAreaSqMeters(rectWorldPts);
  if (rectArea !== 12.0) {
    console.error("Task 6.2 TEST 3 Failed: 4x3 rectangle area != 12", rectArea);
    passed = false;
  }

  // TEST 4: 4 x 3 rectangle: perimeter = 14 m (including closing segment)
  const rectPerim = calculatePolygonPerimeterMeters(rectWorldPts);
  if (rectPerim !== 14.0) {
    console.error("Task 6.2 TEST 4 Failed: 4x3 rectangle perimeter != 14", rectPerim);
    passed = false;
  }

  // TEST 5: 4 x 3 rectangle: centroid = (2.0, 1.5)
  const rectCentroid = calculatePolygonCentroid(rectWorldPts);
  if (
    !rectCentroid ||
    Math.abs(rectCentroid.x - 2.0) > 0.001 ||
    Math.abs(rectCentroid.y - 1.5) > 0.001
  ) {
    console.error("Task 6.2 TEST 5 Failed: 4x3 rectangle centroid != (2.0, 1.5)", rectCentroid);
    passed = false;
  }

  // TEST 6: Triangle: verify known area (6x8 right triangle = 24 m²)
  const triWorldPts: Point2D[] = [
    { x: 0, y: 0 },
    { x: 6, y: 0 },
    { x: 0, y: 8 },
  ];
  const triArea = calculatePolygonAreaSqMeters(triWorldPts);
  if (triArea !== 24.0) {
    console.error("Task 6.2 TEST 6 Failed: Triangle area != 24", triArea);
    passed = false;
  }

  // TEST 7: Concave polygon: verify area using known expected result (L-shape = 36 m²)
  const concaveWorldPts: Point2D[] = [
    { x: 0, y: 0 },
    { x: 6, y: 0 },
    { x: 6, y: 4 },
    { x: 3, y: 4 },
    { x: 3, y: 8 },
    { x: 0, y: 8 },
  ];
  const concaveArea = calculatePolygonAreaSqMeters(concaveWorldPts);
  if (concaveArea !== 36.0) {
    console.error("Task 6.2 TEST 7 Failed: Concave L-shape area != 36", concaveArea);
    passed = false;
  }

  // TEST 8: Closing segment is included in perimeter
  const openPerimSum =
    calculateDistance({ x: 0, y: 0 }, { x: 4, y: 0 }) +
    calculateDistance({ x: 4, y: 0 }, { x: 4, y: 3 }) +
    calculateDistance({ x: 4, y: 3 }, { x: 0, y: 3 }); // = 11m
  if (rectPerim <= openPerimSum) {
    console.error(
      "Task 6.2 TEST 8 Failed: Perimeter did not include closing segment",
      rectPerim,
      openPerimSum
    );
    passed = false;
  }

  // TEST 9: Degenerate polygon does not produce NaN centroid
  const degeneratePts: Point2D[] = [
    { x: 0, y: 0 },
    { x: 5, y: 0 },
    { x: 10, y: 0 }, // Collinear line -> area = 0
  ];
  const degenCentroid = calculatePolygonCentroid(degeneratePts);
  if (degenCentroid !== null && (isNaN(degenCentroid.x) || isNaN(degenCentroid.y))) {
    console.error("Task 6.2 TEST 9 Failed: Degenerate polygon produced NaN centroid", degenCentroid);
    passed = false;
  }

  // TEST 10: Screen-space stroke converted under known viewport gives expected world geometry
  const strokeScreenPts: Point2D[] = [
    worldToScreen({ x: 0, y: 0 }, vp),
    worldToScreen({ x: 4, y: 0 }, vp),
    worldToScreen({ x: 4, y: 3 }, vp),
    worldToScreen({ x: 0, y: 3 }, vp),
  ];
  const testStroke: FreehandStroke = {
    id: "str_test",
    points: strokeScreenPts,
    isDrawing: false,
    isClosed: true,
    createdAt: Date.now(),
  };

  const preview1 = computeRegionPreview(testStroke, vp);
  if (!preview1 || preview1.areaSqMeters !== 12.0 || preview1.perimeterMeters !== 14.0) {
    console.error("Task 6.2 TEST 10 Failed: computeRegionPreview incorrect", preview1);
    passed = false;
  }

  // TEST 11: Completed region retains the same area after simulated pan
  const pannedVp: Viewport = { ...vp, x: vp.x + 350, y: vp.y - 200 };
  if (preview1 && preview1.areaSqMeters !== 12.0) {
    console.error("Task 6.2 TEST 11 Failed: Area changed after simulated pan", preview1.areaSqMeters);
    passed = false;
  }

  // TEST 12: Completed region retains the same area after simulated zoom
  const zoomedVp: Viewport = { scale: 120, x: vp.x, y: vp.y };
  if (preview1 && preview1.areaSqMeters !== 12.0) {
    console.error("Task 6.2 TEST 12 Failed: Area changed after simulated zoom", preview1.areaSqMeters);
    passed = false;
  }

  // TEST 13: Very short stroke produces a controlled invalid/degenerate preview state
  const shortStroke: FreehandStroke = {
    id: "str_short",
    points: [
      { x: 10, y: 10 },
      { x: 12, y: 10 },
    ],
    isDrawing: false,
    isClosed: false,
    createdAt: Date.now(),
  };
  const shortPreview = computeRegionPreview(shortStroke, vp);
  if (shortPreview && shortPreview.isValid !== false) {
    console.error("Task 6.2 TEST 13 Failed: Short stroke was not marked invalid", shortPreview);
    passed = false;
  }

  return passed;
}
