/**
 * Unit tests for Freehand Region Stroke Capture Manager (Task 6.1).
 * Tests stroke lifecycle, point sampling, distance filtering, completion, cancellation, and order preservation.
 */

import {
  startStroke,
  appendPointToStroke,
  completeStroke,
  cancelStroke,
  calculateDistance,
} from "./freehandManager";
import { FreehandStroke } from "./freehandTypes";

export function runFreehandTests(): boolean {
  let passed = true;

  // Test 1: Initial stroke state is null
  let activeStroke: FreehandStroke | null = null;
  if (activeStroke !== null) {
    console.error("Freehand Test 1 Failed: Initial stroke not null", activeStroke);
    passed = false;
  }

  // Test 2: Pointer start creates a stroke
  activeStroke = startStroke({ x: 100, y: 200 });
  if (
    !activeStroke ||
    activeStroke.points.length !== 1 ||
    activeStroke.points[0].x !== 100 ||
    activeStroke.points[0].y !== 200 ||
    !activeStroke.isDrawing ||
    activeStroke.isClosed
  ) {
    console.error("Freehand Test 2 Failed: startStroke incorrect", activeStroke);
    passed = false;
  }

  // Test 3: Pointer movement appends points when distance >= threshold
  activeStroke = appendPointToStroke(activeStroke, { x: 101, y: 200 }, 3); // 1px dist -> skipped
  if (activeStroke.points.length !== 1) {
    console.error("Freehand Test 3a Failed: point within threshold was not filtered", activeStroke);
    passed = false;
  }

  activeStroke = appendPointToStroke(activeStroke, { x: 110, y: 200 }, 3); // 10px dist -> appended
  activeStroke = appendPointToStroke(activeStroke, { x: 110, y: 250 }, 3); // 50px dist -> appended
  if (activeStroke.points.length !== 3) {
    console.error("Freehand Test 3b Failed: points above threshold not appended", activeStroke);
    passed = false;
  }

  // Test 4: Pointer release completes the stroke
  const completed = completeStroke(activeStroke);
  if (!completed || completed.isDrawing !== false || completed.isClosed !== true) {
    console.error("Freehand Test 4 Failed: completeStroke incorrect", completed);
    passed = false;
  }

  // Test 5: Multiple points are preserved in order
  if (
    completed.points[0].x !== 100 ||
    completed.points[1].x !== 110 ||
    completed.points[2].y !== 250
  ) {
    console.error("Freehand Test 5 Failed: Point order corrupted", completed.points);
    passed = false;
  }

  // Test 6: Too-short stroke (< 3 points) is rejected / cancelled cleanly
  let shortStroke = startStroke({ x: 50, y: 50 });
  shortStroke = appendPointToStroke(shortStroke, { x: 60, y: 50 }, 3);
  const rejected = completeStroke(shortStroke);
  if (rejected.points.length !== 0 || rejected.isClosed !== false) {
    console.error("Freehand Test 6 Failed: Short stroke not rejected", rejected);
    passed = false;
  }

  // Test 7: Escape / cancelStroke returns null
  const cancelled = cancelStroke();
  if (cancelled !== null) {
    console.error("Freehand Test 7 Failed: cancelStroke didn't return null");
    passed = false;
  }

  // Test 8: Starting a new stroke replaces previous stroke
  const stroke1 = completeStroke(
    appendPointToStroke(
      appendPointToStroke(startStroke({ x: 0, y: 0 }), { x: 10, y: 0 }),
      { x: 10, y: 10 }
    )
  );
  const stroke2 = startStroke({ x: 300, y: 300 });
  if (stroke2.id === stroke1.id || stroke2.points.length !== 1 || stroke2.points[0].x !== 300) {
    console.error("Freehand Test 8 Failed: New stroke did not replace previous stroke");
    passed = false;
  }

  // Test 9: Screen-space points remain screen-space
  const samplePt = { x: 245.5, y: 380.2 };
  const str = startStroke(samplePt);
  if (str.points[0].x !== 245.5 || str.points[0].y !== 380.2) {
    console.error("Freehand Test 9 Failed: Screen-space point values altered unexpectedly");
    passed = false;
  }

  // Test 10: Distance math sanity check
  const d = calculateDistance({ x: 0, y: 0 }, { x: 3, y: 4 });
  if (Math.abs(d - 5) > 0.0001) {
    console.error("Freehand Test 10 Failed: Distance math incorrect", d);
    passed = false;
  }

  return passed;
}
