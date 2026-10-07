/**
 * Top-level reusable Konva 2D Architectural Canvas wrapper.
 * Combines responsive CanvasStage, Drafting Grid, Viewport Control Bar, World Coordinates Status Bar,
 * Task 5.4 Object Manipulation, Task 6.1 Freehand Region Stroke Capture, and Task 6.2 Live World Region Preview.
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import { LayoutCanvasProps, Viewport, Point2D } from "./canvasTypes";
import { CanvasStage } from "./CanvasStage";
import {
  DEFAULT_INITIAL_SCALE,
  zoomInCenter,
  zoomOutCenter,
  fitBounds,
} from "./viewport";
import { FloorPlanRenderModel } from "../renderer/renderTypes";
import { applyTransform } from "../transforms/transformManager";
import { SnapGuideLine } from "../snapping/snappingTypes";
import { TransformChange } from "../transforms/transformTypes";
import { selectionManager } from "../selection/selectionManager";
import { EditorToolMode, FreehandStroke, RegionPreview } from "../freehand/freehandTypes";
import { computeRegionPreview } from "../freehand/freehandManager";
import { RegionPreviewPanel } from "../freehand/RegionPreviewPanel";

// Default sample floor plan render model for Task 5.3, 5.4, 6.1 & 6.2 validation
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
  spaces: [],
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
  onSwitchFloorPlan,
  onGoToUpload,
  availableFloorPlans,
  activeFloorPlanId,
}) => {
  const initialModel = renderModel || demoModel || SAMPLE_FLOOR_PLAN_RENDER_MODEL;
  const [activeModel, setActiveModel] = useState<FloorPlanRenderModel>(initialModel);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [snapGuides, setSnapGuides] = useState<SnapGuideLine[]>([]);

  // Task 6.1 & 6.2 Freehand State
  const [toolMode, setToolMode] = useState<EditorToolMode>("select");
  const [freehandStroke, setFreehandStroke] = useState<FreehandStroke | null>(null);
  const [regionPreview, setRegionPreview] = useState<RegionPreview | null>(null);

  const [viewport, setViewport] = useState<Viewport>({
    scale: initialScale,
    x: 0,
    y: 0,
  });
  const [containerSize, setContainerSize] = useState<{ width: number; height: number }>({
    width: 800,
    height: 600,
  });
  const [showGrid, setShowGrid] = useState<boolean>(initialShowGrid);
  const [cursorWorldPt, setCursorWorldPt] = useState<Point2D>({ x: 0, y: 0 });
  const fitViewRef = useRef<(() => void) | null>(null);

  // Sync activeModel if external renderModel prop updates and auto fit bounds to floor plan
  useEffect(() => {
    if (renderModel) {
      setActiveModel(renderModel);
      if (containerSize.width > 0 && containerSize.height > 0 && renderModel.boundary.length > 0) {
        setViewport(fitBounds(renderModel.boundary, containerSize.width, containerSize.height));
      }
    }
  }, [renderModel, containerSize]);

  // Compute and lock world region preview when freehand stroke updates
  const handleStrokeChange = useCallback(
    (stroke: FreehandStroke | null) => {
      setFreehandStroke(stroke);
      if (!stroke) {
        setRegionPreview(null);
      } else {
        const preview = computeRegionPreview(stroke, viewport);
        setRegionPreview(preview);
      }
    },
    [viewport]
  );

  const handleClearRegion = useCallback(() => {
    setFreehandStroke(null);
    setRegionPreview(null);
  }, []);

  // Viewport Control Button Actions
  const handleZoomIn = useCallback(() => {
    setViewport((prevVp) => zoomInCenter(prevVp, containerSize.width, containerSize.height));
  }, [containerSize]);

  const handleZoomOut = useCallback(() => {
    setViewport((prevVp) => zoomOutCenter(prevVp, containerSize.width, containerSize.height));
  }, [containerSize]);

  const handleFitView = useCallback(() => {
    if (fitViewRef.current) {
      fitViewRef.current();
    } else if (activeModel && containerSize.width > 0 && containerSize.height > 0) {
      setViewport(fitBounds(activeModel.boundary, containerSize.width, containerSize.height));
    }
  }, [activeModel, containerSize]);

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

  // Selected object details for status bar
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
        backgroundColor: "#000000",
        position: "relative",
      }}
    >
      {/* Top Viewport & Tool Mode Control Bar */}
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
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          {onGoToUpload && (
            <button
              className="btn-ctrl"
              onClick={onGoToUpload}
              title="Go to Upload & Floor Plans Panel"
              style={{ backgroundColor: "#0284c7", color: "#ffffff", borderColor: "#0284c7", fontWeight: 700, padding: "4px 12px" }}
            >
              + Upload / Sidebar
            </button>
          )}

          {availableFloorPlans && availableFloorPlans.length > 0 && onSwitchFloorPlan && (
            <select
              value={activeFloorPlanId || ""}
              onChange={(e) => {
                if (e.target.value) {
                  const savedProj = localStorage.getItem("layouts_ai_active_project_id") || "proj_101";
                  onSwitchFloorPlan(savedProj, e.target.value);
                }
              }}
              style={{
                backgroundColor: "#0f172a",
                border: "1px solid #38bdf8",
                color: "#f8fafc",
                borderRadius: "6px",
                padding: "5px 12px",
                fontSize: "0.8125rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {availableFloorPlans.map((fp) => (
                <option key={fp.id} value={fp.id}>
                  📄 {fp.name}
                </option>
              ))}
            </select>
          )}

          {toolMode === "freehand_region" ? (
            <span style={{ color: "#a855f7", fontWeight: 600, fontSize: "0.875rem" }}>
              SELECT REGION ACTIVE — Click & drag to outline working area
            </span>
          ) : (
            <span style={{ color: "#38bdf8", fontWeight: 600, fontSize: "0.875rem" }}>
              2D CAD Layout Editor
            </span>
          )}
          <span style={{ color: "#64748b", fontSize: "0.75rem" }}>
            (Wheel zooms • Left-drag pan)
          </span>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {/* Tool Modes */}
          <button
            className={`btn-ctrl ${toolMode === "select" ? "btn-ctrl-active" : ""}`}
            onClick={() => setToolMode("select")}
            title="Select & edit objects or pan canvas"
          >
            Select
          </button>
          <button
            className={`btn-ctrl ${toolMode === "freehand_region" ? "btn-ctrl-active" : ""}`}
            onClick={() => {
              setToolMode("freehand_region");
              setSelectedObjectId(null);
            }}
            title="Draw arbitrary spatial region on floor plan"
          >
            Select Region
          </button>

          <span style={{ color: "#475569", margin: "0 4px" }}>|</span>

          {/* Viewport Actions */}
          <button className="btn-ctrl" onClick={handleZoomIn} title="Zoom In around canvas center">
            Zoom In (+)
          </button>
          <button className="btn-ctrl" onClick={handleZoomOut} title="Zoom Out around canvas center">
            Zoom Out (-)
          </button>
          <button className="btn-ctrl" onClick={handleFitView} title="Fit entire floor plan in viewport">
            Fit View
          </button>
          <button
            className={`btn-ctrl ${showGrid ? "btn-ctrl-active" : ""}`}
            onClick={() => setShowGrid(!showGrid)}
            title="Toggle drafting grid visibility"
          >
            {showGrid ? "Grid On" : "Grid Off"}
          </button>

          {freehandStroke && (
            <button
              className="btn-ctrl"
              onClick={handleClearRegion}
              title="Clear captured freehand region"
              style={{ borderColor: "#ef4444", color: "#f87171" }}
            >
              Clear Region
            </button>
          )}
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
          onFitView={(fitFn) => {
            fitViewRef.current = fitFn;
          }}
          onContainerResize={setContainerSize}
          toolMode={toolMode}
          freehandStroke={freehandStroke}
          regionPreview={regionPreview}
          onStrokeChange={handleStrokeChange}
        />

        {/* Task 6.2 Region Preview Info Panel */}
        <RegionPreviewPanel regionPreview={regionPreview} onClear={handleClearRegion} />
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
        <div style={{ color: selectedObjectId ? "#38bdf8" : regionPreview ? "#c084fc" : "#94a3b8", fontWeight: (selectedObjectId || regionPreview) ? 600 : 400 }}>
          {selectedFurniture && (
            <>
              Selected Furniture: [{selectedFurniture.id}] {selectedFurniture.itemType} | Pos: ({selectedFurniture.position.x}m, {selectedFurniture.position.y}m) | Size: {selectedFurniture.widthMeters}m × {selectedFurniture.depthMeters}m | Rot: {selectedFurniture.rotationDeg}° {selectedFurniture.isLocked ? "🔒 [Locked]" : " (Editable)"}
            </>
          )}
          {selectedWall && <>{`Selected Wall: [${selectedWall.id}] (Read-Only Structure)`}</>}
          {selectedDoor && <>{`Selected Door: [${selectedDoor.id}] (Read-Only Aperture)`}</>}
          {selectedWindow && <>{`Selected Window: [${selectedWindow.id}] (Read-Only Aperture)`}</>}
          {selectedColumn && <>{`Selected Column: [${selectedColumn.id}] (Read-Only Structure)`}</>}
          {!selectedObjectId && regionPreview?.isClosed && (
            <>{`Region Preview: ${regionPreview.areaSqMeters.toFixed(2)} m² | Perim: ${regionPreview.perimeterMeters.toFixed(2)} m | Centroid: (${regionPreview.centroid?.x.toFixed(2)}m, ${regionPreview.centroid?.y.toFixed(2)}m)`}</>
          )}
          {!selectedObjectId && !regionPreview?.isClosed && "Selected: None"}
        </div>
        <div>
          Tool: {toolMode.toUpperCase()} | Scale: {viewport.scale.toFixed(1)} px/m
        </div>
      </div>
    </div>
  );
};
