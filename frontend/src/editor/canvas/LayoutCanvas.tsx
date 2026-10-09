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
import { CanvasToolbar } from "../../components/workspace/CanvasToolbar";

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

import {
  generateLayoutCandidates,
  applySuggestionToRenderModel,
  LayoutSuggestionPayload,
  validateRegion,
} from "../../api/layout";


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
  availableStoreys,
  activeStorey,
  onSwitchStorey,
}) => {
  const initialModel = renderModel || demoModel || SAMPLE_FLOOR_PLAN_RENDER_MODEL;
  const [activeModel, setActiveModel] = useState<FloorPlanRenderModel>(initialModel);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [snapGuides, setSnapGuides] = useState<SnapGuideLine[]>([]);

  // Task 6.1 & 6.2 Freehand State
  const [toolMode, setToolMode] = useState<EditorToolMode>("select");
  const [freehandStroke, setFreehandStroke] = useState<FreehandStroke | null>(null);
  const [regionPreview, setRegionPreview] = useState<RegionPreview | null>(null);

  // AI Layout Solver State
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [layoutCandidates, setLayoutCandidates] = useState<LayoutSuggestionPayload[]>([]);
  const [activeCandidateIdx, setActiveCandidateIdx] = useState<number>(0);
  const [promptInput, setPromptInput] = useState<string>("6 Professional Desks + 1 Manager Cabin");

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

  const handleGenerateLayout = async () => {
    const targetFpId = activeFloorPlanId || "fp_501";
    setIsGenerating(true);
    try {
      // Parse requirements from prompt
      let profQty = 6;
      let mgrQty = 1;
      const profMatch = promptInput.match(/(\d+)\s*(?:professional|desk|workstation)/i);
      if (profMatch) profQty = parseInt(profMatch[1]);
      const mgrMatch = promptInput.match(/(\d+)\s*(?:manager|executive|cabin)/i);
      if (mgrMatch) mgrQty = parseInt(mgrMatch[1]);

      const reqs = [
        { item_type: "PROFESSIONAL_DESK", quantity: profQty },
        { item_type: "MANAGER_DESK", quantity: mgrQty },
      ];

      const results = await generateLayoutCandidates({
        floor_plan_id: targetFpId,
        storey_name: activeStorey,
        requirements: reqs,
      });

      setLayoutCandidates(results);
      if (results && results.length > 0) {
        setActiveCandidateIdx(0);
        setActiveModel((prev) => applySuggestionToRenderModel(prev, results[0]));
      }
    } catch (err: any) {
      alert(`AI Layout Generation Error: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectCandidate = (index: number) => {
    if (index >= 0 && index < layoutCandidates.length) {
      setActiveCandidateIdx(index);
      const cand = layoutCandidates[index];
      setActiveModel((prev) => applySuggestionToRenderModel(prev, cand));
    }
  };

  // Compute and lock world region preview when freehand stroke updates
  const [isValidatingRegion, setIsValidatingRegion] = useState<boolean>(false);

  const handleStrokeChange = useCallback(
    (stroke: FreehandStroke | null) => {
      setFreehandStroke(stroke);
      if (!stroke) {
        setRegionPreview(null);
      } else {
        const preview = computeRegionPreview(stroke, viewport);
        setRegionPreview(preview);

        // Automatically validate with backend as soon as a region stroke is closed
        if (stroke.isClosed && !stroke.isDrawing && preview.isValid && preview.worldPoints.length >= 3) {
          const targetFpId = activeFloorPlanId || renderModel?.id || activeModel?.id || "fp_501";
          setIsValidatingRegion(true);
          validateRegion({
            floor_plan_id: targetFpId,
            storey_name: activeStorey,
            world_points: preview.worldPoints,
          })
            .then((response) => {
              setRegionPreview((prev) => {
                if (!prev || prev.strokeId !== preview.strokeId) return prev;
                return {
                  ...prev,
                  serverValidation: {
                    status: response.status,
                    isValid: response.is_valid,
                    isClipped: response.is_clipped,
                    message: response.message,
                    clippedWorldPoints: response.clipped_points,
                    areaSqMeters: response.area_sqm,
                    perimeterMeters: response.perimeter_m,
                    centroid: response.centroid || null,
                  },
                };
              });
            })
            .catch((err) => {
              console.warn("Server Region Validation Notice:", err.message);
            })
            .finally(() => {
              setIsValidatingRegion(false);
            });
        }
      }
    },
    [viewport, activeFloorPlanId, activeStorey]
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
        overflow: "hidden",
        backgroundColor: "#FAFAF8",
        position: "relative",
      }}
    >
      {/* Overlay CAD Drafting Toolbar */}
      <CanvasToolbar
        toolMode={toolMode}
        onSelectToolMode={setToolMode}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onFitView={handleFitView}
        showGrid={showGrid}
        onToggleGrid={() => setShowGrid((prev) => !prev)}
      />

      {/* Konva Stage Container */}
      <div style={{ flex: 1, position: "relative", backgroundColor: "#FAFAF8" }}>
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

        {/* Task 6.2 & 6.3 Region Preview & Authoritative Clipping Info Panel */}
        <RegionPreviewPanel
          regionPreview={regionPreview}
          onClear={handleClearRegion}
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
          {!selectedObjectId && regionPreview?.serverValidation?.isValid && (
            <>{`Authoritative Region (${regionPreview.serverValidation.isClipped ? "Clipped" : "Enclosed"}): ${regionPreview.serverValidation.areaSqMeters.toFixed(2)} m² | Perim: ${regionPreview.serverValidation.perimeterMeters.toFixed(2)} m | Centroid: (${regionPreview.serverValidation.centroid?.x.toFixed(2)}m, ${regionPreview.serverValidation.centroid?.y.toFixed(2)}m)`}</>
          )}
          {!selectedObjectId && !regionPreview?.serverValidation?.isValid && regionPreview?.isClosed && (
            <>{`Region Preview: ${regionPreview.areaSqMeters.toFixed(2)} m² | Perim: ${regionPreview.perimeterMeters.toFixed(2)} m | Centroid: (${regionPreview.centroid?.x.toFixed(2)}m, ${regionPreview.centroid?.y.toFixed(2)}m)`}</>
          )}
          {!selectedObjectId && !regionPreview?.isClosed && "Selected: None"}
        </div>

        <div>
          {activeStorey ? `Storey: ${activeStorey} | ` : ""}
          Tool: {toolMode.toUpperCase()} | Scale: {viewport.scale.toFixed(1)} px/m
        </div>
      </div>
    </div>
  );
};
