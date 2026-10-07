/**
 * Editor Interaction State (Task 5.4).
 * Centralized transient state manager for selection, transformation modes, and snapping guides.
 * CRITICAL: Holds transient UI interaction state only — backend remains authoritative for floor plan geometry.
 */

import { SelectionState } from "../selection/selectionTypes";
import { SnapGuideLine } from "../snapping/snappingTypes";
import { TransformMode } from "../transforms/transformTypes";

export interface EditorState {
  selection: SelectionState;
  interactionMode: TransformMode;
  isTransforming: boolean;
  activeSnapGuides: SnapGuideLine[];
}

export const INITIAL_EDITOR_STATE: EditorState = {
  selection: {
    selectedObjectId: null,
    selectedObjectType: null,
    isLocked: false,
  },
  interactionMode: "idle",
  isTransforming: false,
  activeSnapGuides: [],
};
