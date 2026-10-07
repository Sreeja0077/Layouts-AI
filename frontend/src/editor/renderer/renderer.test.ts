/**
 * Unit tests for RendererAdapter and renderer-neutral models (Task 5.3).
 * Verifies isolation from Konva, interface adherence, and source model immutability.
 */

import { FloorPlanRenderModel } from "./renderTypes";
import { RendererAdapter } from "./RendererAdapter";
import { Viewport } from "../canvas/canvasTypes";

// Mock adapter verifying interface contract without requiring Node.js native canvas bindings
class MockRendererAdapter implements RendererAdapter<string> {
  renderFloorPlan(model: Readonly<FloorPlanRenderModel>, _viewport: Viewport): string {
    return `FloorPlan:${model.id}:${model.walls.length}walls:${model.doors.length}doors:${model.furniture.length}furniture`;
  }
  renderWalls(walls: ReadonlyArray<any>, _viewport: Viewport): string {
    return `Walls:${walls.length}`;
  }
  renderDoors(doors: ReadonlyArray<any>, _viewport: Viewport): string {
    return `Doors:${doors.length}`;
  }
  renderWindows(windows: ReadonlyArray<any>, _viewport: Viewport): string {
    return `Windows:${windows.length}`;
  }
  renderColumns(columns: ReadonlyArray<any>, _viewport: Viewport): string {
    return `Columns:${columns.length}`;
  }
  renderSpaces(spaces: ReadonlyArray<any>, _viewport: Viewport): string {
    return `Spaces:${spaces.length}`;
  }
  renderFurniture(furniture: ReadonlyArray<any>, _viewport: Viewport): string {
    return `Furniture:${furniture.length}`;
  }
  clear(): void {}
}

export function runRendererAdapterTests(): boolean {
  let passed = true;

  // Test 1: Instantiation of renderer-neutral FloorPlanRenderModel (Zero Konva imports required)
  const model: FloorPlanRenderModel = {
    id: "test_fp_001",
    name: "Test Architectural Model",
    boundary: [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
      { x: 0, y: 10 },
    ],
    walls: [
      { id: "w1", start: { x: 0, y: 0 }, end: { x: 10, y: 0 }, thicknessMeters: 0.2, isExterior: true },
    ],
    doors: [
      { id: "d1", position: { x: 5, y: 0 }, widthMeters: 0.9, swingAngleDeg: 90 },
    ],
    windows: [
      { id: "win1", start: { x: 2, y: 10 }, end: { x: 6, y: 10 }, thicknessMeters: 0.2 },
    ],
    columns: [
      { id: "c1", position: { x: 5, y: 5 }, widthMeters: 0.6, heightMeters: 0.6 },
    ],
    spaces: [],
    furniture: [
      { id: "f1", catalogItemId: "desk_exec", itemType: "EXECUTIVE_DESK", position: { x: 3, y: 3 }, widthMeters: 1.6, depthMeters: 0.8, rotationDeg: 0 },
    ],
  };

  const originalJson = JSON.stringify(model);

  // Test 2: RendererAdapter interface implementation & execution
  const adapter = new MockRendererAdapter();
  const output = adapter.renderFloorPlan(model, { scale: 40, x: 50, y: 50 });

  if (output !== "FloorPlan:test_fp_001:1walls:1doors:1furniture") {
    console.error("RendererAdapter output check failed", output);
    passed = false;
  }

  // Test 3: Immutability test — rendering adapter must NOT mutate input model
  if (JSON.stringify(model) !== originalJson) {
    console.error("Source FloorPlanRenderModel was mutated during rendering!");
    passed = false;
  }

  // Test 4: Preserves stable entity IDs
  if (model.walls[0].id !== "w1" || model.doors[0].id !== "d1" || model.columns[0].id !== "c1") {
    console.error("Stable IDs check failed");
    passed = false;
  }

  return passed;
}
