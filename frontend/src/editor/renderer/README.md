# RendererAdapter Architecture & Abstraction Layer (Task 5.3)

## 📌 Purpose & Overview
Decouples canonical domain geometry and layout state from rendering engine implementations (Konva, SVG, Canvas, WebGL). Establishes a renderer-neutral data model (`FloorPlanRenderModel`) that contains zero dependencies on Konva or browser DOM elements.

## 🏗️ Architectural Layers
```
Domain Geometry (Python Authoritative Core)
      ↓
Render Model (renderer-neutral, meters & degrees)
      ↓
RendererAdapter (Abstract Interface)
      ↓
KonvaRendererAdapter (React-Konva Implementation)
      ↓
Konva Stage / Layers
```

## 🔒 Architectural Invariants
1. **Zero Konva Imports in Domain Models:** `renderTypes.ts` contains pure TypeScript interfaces. It never imports `konva`, `react-konva`, or graphics primitives.
2. **Immutable Source Data:** `RendererAdapter` implementations consume render models in read-only mode and NEVER mutate input architectural geometry or entity IDs.
3. **No Business Rules in Renderer:** The renderer visualizes layout state only. Collision checks, free-space calculation, clearance evaluation, and accessibility rules remain 100% owned by the Python backend geometry engine.
4. **Metric World Coordinates:** All spatial dimensions remain in meters (`widthMeters`, `depthMeters`, `x`, `y`) and rotation in degrees (`rotationDeg`). Screen pixel coordinate scaling is handled purely by the viewport transform (`worldToScreen`).

## 📁 Module Organization (`frontend/src/editor/renderer/`)
- `renderTypes.ts`: Renderer-neutral interfaces (`RenderWall`, `RenderDoor`, `RenderWindow`, `RenderColumn`, `RenderFurniture`, `FloorPlanRenderModel`).
- `RendererAdapter.ts`: Abstract `RendererAdapter<TOutput>` interface.
- `KonvaRendererAdapter.tsx`: Konva-specific implementation of `RendererAdapter` and `KonvaFloorPlanRenderer` component.
- `index.ts`: Module exports.
- `renderer.test.ts`: Unit test suite verifying interface adherence, Konva isolation, and input immutability.

## ⚠️ Task Boundaries & Future Scope
- **Task 5.4 (Object Manipulation):** Selection handles, transformers, dragging, rotation, resizing, and snapping assistance. *(Not implemented in Task 5.3)*.
