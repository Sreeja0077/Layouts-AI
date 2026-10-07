# Editor Snapping Assistance Module (Task 5.4)

## 📌 Purpose & Overview
Provides real-time drafting grid snapping (0.25m step) and object alignment snapping in world metric units (meters). Visual snap guides assist users during object drag operations.

## 🔒 Architectural Invariants
- **Metric World Units:** Snapping calculations operate purely in world space (`meters`).
- **Editor Assistance Only:** Snapping is visual CAD alignment assistance; it is NOT authoritative backend geometry validation.
- **Configurable Defaults:** `GRID_SNAP_STEP_METERS = 0.25m`, `SNAP_TOLERANCE_METERS = 0.10m`.
