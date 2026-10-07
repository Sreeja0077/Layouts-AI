# Editor Object Selection Module (Task 5.4)

## 📌 Purpose & Overview
Manages single-object selection state using stable domain identifiers (`string`). Supports selecting editable furniture and highlighting read-only structural elements (`WALL`, `DOOR`, `WINDOW`, `COLUMN`).

## 🔒 Architectural Invariants
- **Stable Identifiers:** Selection is tracked strictly by stable domain ID (`selectedObjectId: string | null`), never by temporary array indexes or screen coordinates.
- **Single Selection:** Exactly zero or one object is selected at any given time.
- **Locked Metadata:** Objects with `isLocked: true` or structural elements return `isLocked = true` in selection state to disable drag, rotate, and resize operations.
