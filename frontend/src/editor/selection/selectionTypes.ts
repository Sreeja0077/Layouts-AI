/**
 * TypeScript contracts for Editor Object Selection (Task 5.4).
 * Manages single-object selection using stable domain identifiers.
 */

export interface SelectionState {
  /** Selected entity stable ID or null if no object is selected */
  selectedObjectId: string | null;
  /** Category of selected element */
  selectedObjectType: "FURNITURE" | "WALL" | "DOOR" | "WINDOW" | "COLUMN" | null;
  /** Whether the selected element is locked for editing */
  isLocked: boolean;
}
