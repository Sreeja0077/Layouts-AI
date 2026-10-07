/**
 * LayoutCanvas Component (Task 5.2 & Task 5.3).
 * Top-level reusable Konva 2D Architectural Canvas wrapper.
 * Combines responsive CanvasStage, Drafting Grid, Viewport Toolbar Controls, and World Coordinates Status Display.
 * Consumes renderer-neutral FloorPlanRenderModel via RendererAdapter architecture.
 */

import React, { useState, useCallback, useEffect } from "react";
import { LayoutCanvasProps, Viewport, Point2D } from "./canvasTypes";
import { CanvasStage } from "./CanvasStage";
import { DEFAULT_INITIAL_SCALE, zoomAtPoint } from "./viewport";
import { FloorPlanRenderModel } from "../renderer/renderTypes";
import { applyTransform } from "../transforms/transformManager";
import { SnapGuideLine } from "../snapping/snappingTypes";
import { TransformChange } from "../transforms/transformTypes";
import { selectionManager } from "../selection/selectionManager";

// Sample renderer-neutral architectural floor plan model for Task 5.3 & Task 5.4 validation
const SAMPLE_FLOOR_PLAN_RENDER_MODEL: FloorPlanRenderModel = {
  id: "rm_101",
  name: "Executive Office Suite A",
  boundary: [
    { x: 0, y: 0 },
    { x: 12, y: 0 },
    { x: 12, y: 8 },
    { x: 0, y: 8 },
  ],
  walls: [
    { id: "w1", start: { x: 0, y: 0 }, end: { x: 12, y: 0 }, thicknessMeters: 0.2, isExterior: true },
    { id: "w2", start: { x: 12, y: 0 }, end: { x: 12, y: 8 }, thicknessMeters: 0.2, isExterior: true },
    { id: "w3", start: { x: 12, y: 8 }, end: { x: 0, y: 8 }, thicknessMeters: 0.2, isExterior: true },
    { id: "w4", start: { x: 0, y: 8 }, end: { x: 0, y: 0 }, thicknessMeters: 0.2, isExterior: true },
    { id: "w_int_1", start: { x: 6, y: 0 }, end: { x: 6, y: 5 }, thicknessMeters: 0.15, isExterior: false },
  ],
  doors: [
    { id: "d1", position: { x: 3, y: 0 }, widthMeters: 0.9, swingAngleDeg: 90 },
  ],
  windows: [
    { id: "win1", start: { x: 2, y: 8 }, end: { x: 5, y: 8 }, thicknessMeters: 0.2 },
  ],
  columns: [
    { id: "col1", position: { x: 9, y: 4 }, widthMeters: 0.6, heightMeters: 0.6 },
  ],
  furniture: [
    { id: "f1", catalogItemId: "desk_exec", itemType: "EXECUTIVE_DESK", position: { x: 3, y: 4 }, widthMeters: 1.8, depthMeters: 0.9, rotationDeg: 0, isLocked: false },
    { id: "f2", catalogItemId: "chair_exec", itemType: "TASK_CHAIR", position: { x: 3, y: 5.2 }, widthMeters: 0.6, depthMeters: 0.6, rotationDeg: 0, isLocked: false },
    { id: "f_locked", catalogItemId: "cabinet_fixed", itemType: "STORAGE_CABINET", position: { x: 9, y: 2 }, widthMeters: 1.2, depthMeters: 0.6, rotationDeg: 0, isLocked: true },
  ],
};

export const LayoutCanvas: React.FC<LayoutCanvasProps> = ({
  initialScale = DEFAULT_INITIAL_SCALE,
  showGrid: initialShowGrid = true,
  renderModel,
  demoModel,
  className = "",
}) => {
  const initialModel = renderModel || demoModel || SAMPLE_FLOOR_PLAN_RENDER_MODEL;
  const [activeModel, setActiveModel] = useState<FloorPlanRenderModel>(initialModel);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [snapGuides, setSnapGuides] = useState<SnapGuideLine[]>([]);

  const [viewport, setViewport] = useState<Viewport>({
    scale: initialScale,
    x: 80,
    y: 80,
  });
  const [showGrid, setShowGrid] = useState<boolean>(initialShowGrid);
  const [cursorWorldPt, setCursorWorldPt] = useState<Point2D>({ x: 0, y: 0 });

  // Sync activeModel if external renderModel prop updates
  useEffect(() => {
    if (renderModel) {
      setActiveModel(renderModel);
    }
  }, [renderModel]);

  const handleZoomIn = useCallback(() => {
    setViewport((prev) => zoomAtPoint({ x: 400, y: 300 }, 1.25, prev));
  }, []);

  const handleZoomOut = useCallback(() => {
    setViewport((prev) => zoomAtPoint({ x: 400, y: 300 }, 0.8, prev));
  }, []);

  const handleResetView = useCallback(() => {
    setViewport({ scale: initialScale, x: 80, y: 80 });
  }, [initialScale]);

  const handleSelectObject = useCallback(
    (id: string | null) => {
      setSelectedObjectId(id);
      selectionManager.selectObject(id, activeModel);
      setSnapGuides([]);
    },
    [activeModel]
  );

  const handleTransformChange = useCallback((change: TransformChange) => {
    setActiveModel((prevModel) => applyTransform(prevModel, change));
  }, []);

  // Determine currently selected object details for UI status bar
  const selectedFurniture = activeModel.furniture.find((f) => f.id === selectedObjectId);
  const selectedWall = activeModel.walls.find((w) => w.id === selectedObjectId);
  const selectedDoor = activeModel.doors.find((d) => d.id === selectedObjectId);
  const selectedWindow = activeModel.windows.find((w) => w.id === selectedObjectId);
  const selectedColumn = activeModel.columns.find((c) => c.id === selectedObjectId);

  return (
    <div
      className={`layout-canvas-wrapper ${className}`}
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        minHeight: "450px",
        borderRadius: "8px",
        overflow: "hidden",
        border: "1px solid #334155",
        backgroundColor: "#0f172a",
        position: "relative",
      }}
    >
      {/* Top Viewport Control Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          backgroundColor: "#1e293b",
          borderBottom: "1px solid #334155",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{ color: "#38bdf8", fontWeight: 600, fontSize: "0.875rem" }}>
            2D CAD Layout Editor (Select / Drag / Rotate / Resize / Snap)
          </span>
          <span style={{ color: "#64748b", fontSize: "0.75rem" }}>
            (Shift+Drag or Middle Mouse to Pan • Click Furniture to Drag/Rotate/Resize • Esc to Deselect)
          </span>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleZoomIn}
            style={{
              backgroundColor: "#334155",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            Zoom +
          </button>
          <button
            onClick={handleZoomOut}
            style={{
              backgroundColor: "#334155",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            Zoom -
          </button>
          <button
            onClick={handleResetView}
            style={{
              backgroundColor: "#334155",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            Reset
          </button>
          <button
            onClick={() => setShowGrid(!showGrid)}
            style={{
              backgroundColor: showGrid ? "#0284c7" : "#334155",
              color: "#f8fafc",
              border: "none",
              borderRadius: "4px",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            {showGrid ? "Grid On" : "Grid Off"}
          </button>
        </div>
      </div>

      {/* Konva Stage Container */}
      <div style={{ flex: 1, position: "relative" }}>
        <CanvasStage
          viewport={viewport}
          onViewportChange={setViewport}
          onCursorMove={setCursorWorldPt}
          showGrid={showGrid}
          renderModel={activeModel}
          selectedObjectId={selectedObjectId}
          onSelectObject={handleSelectObject}
          onTransformChange={handleTransformChange}
          onSnapGuidesChange={setSnapGuides}
          snapGuides={snapGuides}
        />
      </div>

      {/* Bottom Status & Coordinates Display */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "6px 16px",
          backgroundColor: "#1e293b",
          borderTop: "1px solid #334155",
          fontSize: "0.75rem",
          color: "#94a3b8",
        }}
      >
        <div>
          World Coordinates: X = {cursorWorldPt.x.toFixed(2)} m, Y = {cursorWorldPt.y.toFixed(2)} m
        </div>
        <div style={{ color: selectedObjectId ? "#38bdf8" : "#94a3b8", fontWeight: selectedObjectId ? 600 : 400 }}>
          {selectedFurniture && (
            <>
              Selected Furniture: [{selectedFurniture.id}] {selectedFurniture.itemType} | Pos: ({selectedFurniture.position.x}m, {selectedFurniture.position.y}m) | Size: {selectedFurniture.widthMeters}m × {selectedFurniture.depthMeters}m | Rot: {selectedFurniture.rotationDeg}° {selectedFurniture.isLocked ? "🔒 [Locked]" : " (Editable)"}
            </>
          )}
          {selectedWall && <>{`Selected Wall: [${selectedWall.id}] (Read-Only Structure)`}</>}
          {selectedDoor && <>{`Selected Door: [${selectedDoor.id}] (Read-Only Aperture)`}</>}
          {selectedWindow && <>{`Selected Window: [${selectedWindow.id}] (Read-Only Aperture)`}</>}
          {selectedColumn && <>{`Selected Column: [${selectedColumn.id}] (Read-Only Structure)`}</>}
          {!selectedObjectId && "Selected: None"}
        </div>
        <div>
          Scale: {viewport.scale.toFixed(1)} px/m | Snap Step: 0.25m
        </div>
      </div>
    </div>
  );
};

