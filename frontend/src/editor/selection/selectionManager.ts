/**
 * Selection Manager for 2D Architectural Editor (Task 5.4).
 * Pure selection logic using stable domain IDs.
 * Enforces single-selection policy and locked entity metadata flags.
 */

import { SelectionState } from "./selectionTypes";
import { FloorPlanRenderModel, RenderFurniture } from "../renderer/renderTypes";

export class SelectionManager {
  private state: SelectionState = {
    selectedObjectId: null,
    selectedObjectType: null,
    isLocked: false,
  };

  /** Returns current selection state */
  public getSelection(): Readonly<SelectionState> {
    return { ...this.state };
  }

  /**
   * Selects an object by stable ID within the floor plan render model.
   */
  public selectObject(objectId: string | null, model?: FloorPlanRenderModel): Readonly<SelectionState> {
    if (!objectId || !model) {
      this.clearSelection();
      return this.getSelection();
    }

    // Check furniture
    const furn = model.furniture.find((item) => item.id === objectId);
    if (furn) {
      this.state = {
        selectedObjectId: furn.id,
        selectedObjectType: "FURNITURE",
        isLocked: !!furn.isLocked,
      };
      return this.getSelection();
    }

    // Check columns
    const col = model.columns.find((item) => item.id === objectId);
    if (col) {
      this.state = {
        selectedObjectId: col.id,
        selectedObjectType: "COLUMN",
        isLocked: true, // Columns read-only by default
      };
      return this.getSelection();
    }

    // Check walls
    const wall = model.walls.find((item) => item.id === objectId);
    if (wall) {
      this.state = {
        selectedObjectId: wall.id,
        selectedObjectType: "WALL",
        isLocked: true, // Walls read-only by default
      };
      return this.getSelection();
    }

    // Check doors
    const door = model.doors.find((item) => item.id === objectId);
    if (door) {
      this.state = {
        selectedObjectId: door.id,
        selectedObjectType: "DOOR",
        isLocked: true, // Doors read-only by default
      };
      return this.getSelection();
    }

    // Check windows
    const win = model.windows.find((item) => item.id === objectId);
    if (win) {
      this.state = {
        selectedObjectId: win.id,
        selectedObjectType: "WINDOW",
        isLocked: true, // Windows read-only by default
      };
      return this.getSelection();
    }

    // If ID not found in model
    this.clearSelection();
    return this.getSelection();
  }

  /** Clears selection state */
  public clearSelection(): Readonly<SelectionState> {
    this.state = {
      selectedObjectId: null,
      selectedObjectType: null,
      isLocked: false,
    };
    return this.getSelection();
  }
}

export const selectionManager = new SelectionManager();
