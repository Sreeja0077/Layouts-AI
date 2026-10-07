/**
 * Unit tests for Selection Manager (Task 5.4).
 * Tests stable ID selection, clearing, locked object flags, and invalid ID handling.
 */

import { SelectionManager } from "./selectionManager";
import { FloorPlanRenderModel } from "../renderer/renderTypes";

export function runSelectionTests(): boolean {
  let passed = true;
  const mgr = new SelectionManager();

  const model: FloorPlanRenderModel = {
    id: "fp_1",
    boundary: [],
    walls: [{ id: "w1", start: { x: 0, y: 0 }, end: { x: 10, y: 0 }, thicknessMeters: 0.2 }],
    doors: [{ id: "d1", position: { x: 3, y: 0 }, widthMeters: 0.9 }],
    windows: [],
    columns: [{ id: "c1", position: { x: 5, y: 5 }, widthMeters: 0.6, heightMeters: 0.6 }],
    furniture: [
      { id: "f1", catalogItemId: "desk_exec", itemType: "EXECUTIVE_DESK", position: { x: 2, y: 2 }, widthMeters: 1.6, depthMeters: 0.8, rotationDeg: 0, isLocked: false },
      { id: "f_locked", catalogItemId: "cab_fixed", itemType: "STORAGE_CABINET", position: { x: 8, y: 2 }, widthMeters: 1.0, depthMeters: 0.5, rotationDeg: 0, isLocked: true },
    ],
  };

  // Test 1: Select unlocked furniture
  let sel = mgr.selectObject("f1", model);
  if (sel.selectedObjectId !== "f1" || sel.selectedObjectType !== "FURNITURE" || sel.isLocked !== false) {
    console.error("Selection Test 1 Failed", sel);
    passed = false;
  }

  // Test 2: Select locked furniture
  sel = mgr.selectObject("f_locked", model);
  if (sel.selectedObjectId !== "f_locked" || sel.selectedObjectType !== "FURNITURE" || sel.isLocked !== true) {
    console.error("Selection Test 2 (Locked) Failed", sel);
    passed = false;
  }

  // Test 3: Select wall (read-only)
  sel = mgr.selectObject("w1", model);
  if (sel.selectedObjectId !== "w1" || sel.selectedObjectType !== "WALL" || sel.isLocked !== true) {
    console.error("Selection Test 3 (Wall) Failed", sel);
    passed = false;
  }

  // Test 4: Clear selection
  sel = mgr.clearSelection();
  if (sel.selectedObjectId !== null || sel.selectedObjectType !== null) {
    console.error("Selection Test 4 (Clear) Failed", sel);
    passed = false;
  }

  // Test 5: Invalid ID deselection
  sel = mgr.selectObject("non_existent_id", model);
  if (sel.selectedObjectId !== null) {
    console.error("Selection Test 5 (Invalid ID) Failed", sel);
    passed = false;
  }

  return passed;
}
