/**
 * Standalone Test Suite Runner for 2D Architectural Editor (Task 5.2, 5.3, 5.4 & Task 6.1).
 * Executes pure unit tests for Viewport, Selection Manager, Snapping Engine, Object Transforms, and Freehand Stroke Capture.
 */

import { runViewportTests } from "./canvas/viewport.test";
import { runSelectionTests } from "./selection/selection.test";
import { runSnappingTests } from "./snapping/snapping.test";
import { runTransformTests } from "./transforms/transforms.test";
import { runFreehandTests } from "./freehand/freehand.test";

export function runAllEditorTests(): boolean {
  console.log("==========================================");
  console.log("RUNNING EDITOR UNIT TEST SUITE (Task 6.1)");
  console.log("==========================================");

  let allPassed = true;

  console.log("\n[1/5] Running Viewport Unit Tests...");
  const vpPassed = runViewportTests();
  console.log(`Viewport Tests: ${vpPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!vpPassed) allPassed = false;

  console.log("\n[2/5] Running Selection Manager Unit Tests...");
  const selPassed = runSelectionTests();
  console.log(`Selection Tests: ${selPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!selPassed) allPassed = false;

  console.log("\n[3/5] Running Snapping Engine Unit Tests...");
  const snapPassed = runSnappingTests();
  console.log(`Snapping Tests: ${snapPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!snapPassed) allPassed = false;

  console.log("\n[4/5] Running Transform Manager Unit Tests...");
  const xformPassed = runTransformTests();
  console.log(`Transform Tests: ${xformPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!xformPassed) allPassed = false;

  console.log("\n[5/5] Running Freehand Stroke Capture Unit Tests...");
  const freehandPassed = runFreehandTests();
  console.log(`Freehand Tests: ${freehandPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!freehandPassed) allPassed = false;

  console.log("\n==========================================");
  console.log(`FINAL RESULT: ${allPassed ? "ALL 5 SUITES PASSED ✅" : "SOME SUITES FAILED ❌"}`);
  console.log("==========================================");

  return allPassed;
}

// Execute tests automatically when imported or run directly
declare const process: any;
if (typeof process !== "undefined" && process?.env?.RUN_EDITOR_TESTS === "true") {
  const result = runAllEditorTests();
  if (!result && typeof process.exit === "function") {
    process.exit(1);
  }
}
