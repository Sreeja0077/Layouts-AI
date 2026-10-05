/**
 * Abstract RendererAdapter Interface (Task 5.3).
 * Decouples canonical domain geometry and layout state from specific rendering engines (Konva, SVG, WebGL).
 * Ensures zero business logic or domain mutation exists within the rendering layer.
 */

import {
  FloorPlanRenderModel,
  RenderWall,
  RenderDoor,
  RenderWindow,
  RenderColumn,
  RenderFurniture,
} from "./renderTypes";
import { Viewport } from "../canvas/canvasTypes";

export interface RendererAdapter<TOutput = unknown> {
  /** Renders the complete floor plan model */
  renderFloorPlan(model: Readonly<FloorPlanRenderModel>, viewport: Viewport): TOutput;

  /** Renders architectural walls */
  renderWalls(walls: ReadonlyArray<RenderWall>, viewport: Viewport): TOutput;

  /** Renders architectural doors */
  renderDoors(doors: ReadonlyArray<RenderDoor>, viewport: Viewport): TOutput;

  /** Renders architectural windows */
  renderWindows(windows: ReadonlyArray<RenderWindow>, viewport: Viewport): TOutput;

  /** Renders structural columns */
  renderColumns(columns: ReadonlyArray<RenderColumn>, viewport: Viewport): TOutput;

  /** Renders furniture objects */
  renderFurniture(furniture: ReadonlyArray<RenderFurniture>, viewport: Viewport): TOutput;

  /** Clears any active render state */
  clear(): void;
}
