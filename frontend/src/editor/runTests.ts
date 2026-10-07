/**
 * Standalone Test Suite Runner for 2D Architectural Editor (Task 5.2, 5.3, 5.4).
 * Executes pure unit tests for Viewport transformations, Selection Manager, Snapping Engine, and Object Transforms.
 */

import { runViewportTests } from "./canvas/viewport.test";
import { runSelectionTests } from "./selection/selection.test";
import { runSnappingTests } from "./snapping/snapping.test";
import { runTransformTests } from "./transforms/transforms.test";

export function runAllEditorTests(): boolean {
  console.log("==========================================");
  console.log("RUNNING EDITOR UNIT TEST SUITE (Task 5.4)");
  console.log("==========================================");

  let allPassed = true;

  console.log("\n[1/4] Running Viewport Unit Tests...");
  const vpPassed = runViewportTests();
  console.log(`Viewport Tests: ${vpPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!vpPassed) allPassed = false;

  console.log("\n[2/4] Running Selection Manager Unit Tests...");
  const selPassed = runSelectionTests();
  console.log(`Selection Tests: ${selPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!selPassed) allPassed = false;

  console.log("\n[3/4] Running Snapping Engine Unit Tests...");
  const snapPassed = runSnappingTests();
  console.log(`Snapping Tests: ${snapPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!snapPassed) allPassed = false;

  console.log("\n[4/4] Running Transform Manager Unit Tests...");
  const xformPassed = runTransformTests();
  console.log(`Transform Tests: ${xformPassed ? "PASSED ✅" : "FAILED ❌"}`);
  if (!xformPassed) allPassed = false;

  console.log("\n==========================================");
  console.log(`FINAL RESULT: ${allPassed ? "ALL 4 SUITES PASSED ✅" : "SOME SUITES FAILED ❌"}`);
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

