# Freehand Region Selection Module (Task 6.1)

## 📌 Purpose & Overview
Captures user freehand pointer strokes on the 2D floor plan canvas to define arbitrary spatial working regions for AI-assisted layout generation.

## 🏗️ Architecture & Stroke Lifecycle
```
User Pointer Down (on stage)
        ↓
startStroke({ x, y }) [screen-space pixels]
        ↓
User Pointer Move
        ↓
appendPointToStroke() [distance sampling threshold ≥ 3px]
        ↓
Live Overlay Rendering (FreehandRegionLayer: magenta #a855f7)
        ↓
User Pointer Up
        ↓
completeStroke() → FreehandStroke { isDrawing: false, isClosed: true }
```

## 🔒 Invariants & Task Boundaries
- **Screen-Space Storage:** Task 6.1 captures and stores points purely in screen-space canvas stage coordinates (`Point2D[]`).
- **No Authoritative Geometry:** Task 6.1 does NOT convert points to world coordinates, call Shapely, perform polygon clipping, or estimate area/centroids. (Those belong to Task 6.2 and 6.3).
- **Zero Furniture / Viewport Interruption:** Freehand drawing mode (`"freehand_region"`) is explicitly isolated from normal furniture selection/dragging and viewport panning modes (`"select"`, `"pan"`).
