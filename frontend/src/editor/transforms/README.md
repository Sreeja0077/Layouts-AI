# Editor Object Transformation Module (Task 5.4)

## 📌 Purpose & Overview
Manages object move, rotation, and resize operations in world metric units (`meters` and `degrees`).

## 🔒 Architectural Invariants
- **World Metric Coordinates:** Transforms operate on world metric positions (`meters`), rotation in degrees (`rotationDeg`), and dimensions (`widthMeters`, `depthMeters`).
- **Locked Entity Protection:** Objects with `isLocked === true` reject all move, rotate, and resize operations.
- **Minimum Dimension Bounds:** Prevents zero, negative, or mirrored object sizes by clamping dimensions to `MIN_FURNITURE_DIMENSION_METERS = 0.10m`.
- **Immutable Updates:** Returns new copy of `FloorPlanRenderModel` without mutating source inputs in-place.
