# Konva 2D Architectural Canvas Stage (Task 5.2)

## 📌 Purpose & Overview
Provides the reusable Konva 2D rendering surface for architectural floor-plan visualization. Supports responsive viewport bounds, world metric coordinate transformations (meters), pointer-anchored zooming, canvas panning, and visual drafting grid overlays.

## 🏗️ Architectural Invariants
- **System Authority:** Python backend owns authoritative geometry, validation, free-space, and spatial optimization. Konva acts purely as a rendering and interaction surface.
- **World Coordinates:** Spatial positions are defined in architectural meters (`X`, `Y` in meters). Screen canvas pixels are computed dynamically via pure viewport transformation functions (`worldToScreen`, `screenToWorld`).
- **Visual Assistance:** The drafting grid (`CanvasGrid`) provides visual spatial reference only and is strictly decoupled from collision, containment, or layout validation.

## 📐 Viewport Model & Coordinate Transformations
`Viewport = { scale: number (px/m), x: number (px), y: number (px) }`
- **World → Screen:** `screenX = worldX * scale + offsetX`, `screenY = worldY * scale + offsetY`
- **Screen → World:** `worldX = (screenX - offsetX) / scale`, `worldY = (screenY - offsetY) / scale`
- **Zooming:** Mouse wheel zoom is anchored at the cursor pointer location (`zoomAtPoint`), keeping the world position under the mouse pointer visually stationary during scaling.
- **Panning:** Canvas panning adjusts screen offsets (`x`, `y`) without mutating underlying architectural geometry.

## 🧱 Module Organization (`frontend/src/editor/canvas/`)
- `canvasTypes.ts`: TypeScript contracts for `Viewport`, `Point2D`, `DemoRenderModel`, and `LayoutCanvasProps`.
- `viewport.ts`: Pure, testable coordinate transformation and scale-clamping functions.
- `CanvasGrid.tsx`: Konva grid layer rendering 1.0m major and 0.25m minor drafting grid lines.
- `CanvasStage.tsx`: Responsive Konva `<Stage>` and `<Layer>` hierarchy with event listeners.
- `LayoutCanvas.tsx`: Top-level wrapper component combining stage, toolbar zoom controls, and coordinate status bar.
- `index.ts`: Package entrypoint re-exporting all canvas modules.

## ⚠️ Task Boundaries & Future Scope
- **Task 5.3 (RendererAdapter):** Decouples domain entities from Konva canvas details using adapter contracts. *(Not implemented in Task 5.2)*.
- **Task 5.4 (Object Manipulation):** Selection handles, dragging, rotation, resizing, and snapping assistance. *(Not implemented in Task 5.2)*.
