/**
 * Konva Canvas Stage Component (Task 5.2, 5.3, 5.4, 6.1 & 6.2).
 * Handles responsive sizing, CAD free canvas pan, cursor-anchored zoom, double-click zoom-to-point,
 * floor-plan rendering via RendererAdapter, and Task 6.1/6.2 Freehand Region Stroke Capture & Preview.
 */

import React, { useRef, useEffect, useState, useCallback } from "react";
import { Stage, Layer } from "react-konva";
import Konva from "konva";
import { Viewport, Point2D } from "./canvasTypes";
import { CanvasGrid } from "./CanvasGrid";
import { screenToWorld, zoomAtPoint, fitBounds } from "./viewport";
import { FloorPlanRenderModel } from "../renderer/renderTypes";
import { KonvaFloorPlanRenderer } from "../renderer/KonvaRendererAdapter";
import { SnapGuideLine } from "../snapping/snappingTypes";
import { TransformChange } from "../transforms/transformTypes";
import { EditorToolMode, FreehandStroke, RegionPreview } from "../freehand/freehandTypes";
import { startStroke, appendPointToStroke, completeStroke } from "../freehand/freehandManager";
import { FreehandRegionLayer } from "../freehand/FreehandRegionLayer";

interface CanvasStageProps {
  viewport: Viewport;
  onViewportChange: (newViewport: Viewport) => void;
  onCursorMove?: (worldPt: Point2D) => void;
  showGrid?: boolean;
  renderModel?: FloorPlanRenderModel;
  selectedObjectId?: string | null;
  onSelectObject?: (id: string | null) => void;
  onTransformChange?: (change: TransformChange) => void;
  onSnapGuidesChange?: (guides: SnapGuideLine[]) => void;
  snapGuides?: SnapGuideLine[];
  onFitView?: (fitFn: () => void) => void;
  onContainerResize?: (size: { width: number; height: number }) => void;
  // Task 6.1 / 6.2 Freehand Region Props
  toolMode?: EditorToolMode;
  freehandStroke?: FreehandStroke | null;
  regionPreview?: RegionPreview | null;
  onStrokeChange?: (stroke: FreehandStroke | null) => void;
}

function getModelBoundingPoints(model: FloorPlanRenderModel): Point2D[] {
  // The render model boundary is already scoped to the active storey/floor plan.
  // Do not include unrelated elements from other IFC storeys when fitting the view.
  if (Array.isArray(model.boundary) && model.boundary.length >= 3) {
    return model.boundary;
  }

  return [];
}

export const CanvasStage: React.FC<CanvasStageProps> = ({
  viewport,
  onViewportChange,
  onCursorMove,
  showGrid = true,
  renderModel,
  selectedObjectId = null,
  onSelectObject,
  onTransformChange,
  onSnapGuidesChange,
  snapGuides = [],
  onFitView,
  onContainerResize,
  toolMode = "select",
  freehandStroke = null,
  regionPreview = null,
  onStrokeChange,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const hasFittedRef = useRef<string | null>(null);

  const [containerSize, setContainerSize] = useState<{ width: number; height: number }>({
    width: 800,
    height: 600,
  });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Responsive container measurement
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && entry.contentRect) {
        const width = Math.max(200, Math.floor(entry.contentRect.width));
        const height = Math.max(200, Math.floor(entry.contentRect.height));
        setContainerSize({ width, height });
        onContainerResize?.({ width, height });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [onContainerResize]);

  // Fit bounds helper
  const fitView = useCallback(() => {
    if (renderModel && containerSize.width > 0 && containerSize.height > 0) {
      const boundingPts = getModelBoundingPoints(renderModel);
      const fittedVp = fitBounds(boundingPts, containerSize.width, containerSize.height);
      onViewportChange(fittedVp);
    }
  }, [renderModel, containerSize, onViewportChange]);

  // Initial fit when model first loads or the active IFC storey changes.
  useEffect(() => {
    if (!renderModel || containerSize.width <= 0 || containerSize.height <= 0) return;

    const fitKey = `${renderModel.id}::${renderModel.activeStorey || "__all__"}`;
    if (hasFittedRef.current === fitKey) return;

    hasFittedRef.current = fitKey;
    fitView();
  }, [renderModel, containerSize.width, containerSize.height, fitView]);

  // Pass fitView callback to parent
  useEffect(() => {
    onFitView?.(fitView);
  }, [onFitView, fitView]);

  // Escape key listener to clear selection or freehand stroke
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onSelectObject?.(null);
        onSnapGuidesChange?.([]);
        onStrokeChange?.(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onSelectObject, onSnapGuidesChange, onStrokeChange]);

  // Cursor-anchored wheel zoom
  const handleWheel = useCallback(
    (e: Konva.KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();
      const stage = stageRef.current;
      if (!stage) return;

      const pointer = stage.getPointerPosition();
      if (!pointer) return;

      const zoomFactor = e.evt.deltaY < 0 ? 1.1 : 0.9;
      onViewportChange(zoomAtPoint(pointer, zoomFactor, viewport));
    },
    [viewport, onViewportChange]
  );

  // Double click zoom to point
  const handleDoubleClick = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      const stage = stageRef.current;
      if (!stage) return;

      const pointer = stage.getPointerPosition();
      if (!pointer) return;

      onViewportChange(zoomAtPoint(pointer, 1.5, viewport));
    },
    [viewport, onViewportChange]
  );

  // Mouse move for coordinates, active panning, and live freehand stroke recording
  const handleMouseMove = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      const stage = stageRef.current;
      if (!stage) return;

      const pointer = stage.getPointerPosition();
      if (pointer && onCursorMove) {
        onCursorMove(screenToWorld(pointer, viewport));
      }

      // 1. Task 6.1 Freehand Region Drawing Active
      if (toolMode === "freehand_region" && freehandStroke && freehandStroke.isDrawing && pointer) {
        const updated = appendPointToStroke(freehandStroke, pointer);
        if (updated !== freehandStroke) {
          onStrokeChange?.(updated);
        }
        return;
      }

      // 2. Viewport Panning Active
      if (isPanning) {
        const dx = e.evt.clientX - panStartRef.current.x;
        const dy = e.evt.clientY - panStartRef.current.y;
        panStartRef.current = { x: e.evt.clientX, y: e.evt.clientY };

        onViewportChange({
          ...viewport,
          x: viewport.x + dx,
          y: viewport.y + dy,
        });
      }
    },
    [toolMode, freehandStroke, isPanning, viewport, onViewportChange, onCursorMove, onStrokeChange]
  );

  // Mouse down for freehand drawing start vs free canvas panning & selection
  const handleMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      const stage = stageRef.current;
      if (!stage) return;

      const pointer = stage.getPointerPosition();
      const targetIsStage = e.target === e.target.getStage();
      const isMiddleClick = e.evt.button === 1;
      const isShiftLeftClick = e.evt.button === 0 && e.evt.shiftKey;

      // Task 6.1: Freehand Region Drawing Mode
      if (toolMode === "freehand_region" && e.evt.button === 0 && !isShiftLeftClick && pointer) {
        onSelectObject?.(null);
        const newStroke = startStroke(pointer);
        onStrokeChange?.(newStroke);
        return;
      }

      // Normal Mode: Left click on an interactive object (furniture, wall, door, window, column) -> do not pan
      if (!targetIsStage && e.evt.button === 0 && !e.evt.shiftKey) {
        return;
      }

      // Middle click, Shift + Left click, or Left click on empty background -> start viewport pan
      if (e.evt.button === 0 || isMiddleClick || isShiftLeftClick) {
        setIsPanning(true);
        panStartRef.current = { x: e.evt.clientX, y: e.evt.clientY };

        if (targetIsStage) {
          onSelectObject?.(null);
        }
      }
    },
    [toolMode, onSelectObject, onStrokeChange]
  );

  // Mouse up to complete freehand stroke or end panning
  const handleMouseUp = useCallback(() => {
    if (toolMode === "freehand_region" && freehandStroke && freehandStroke.isDrawing) {
      const finished = completeStroke(freehandStroke);
      onStrokeChange?.(finished);
    }
    setIsPanning(false);
  }, [toolMode, freehandStroke, onStrokeChange]);

  // Compute cursor style based on tool mode and active pan
  const cursorStyle = React.useMemo(() => {
    if (isPanning) return "grabbing";
    if (toolMode === "freehand_region") return "crosshair";
    return "default";
  }, [isPanning, toolMode]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        backgroundColor: "#FFFFFF",
        cursor: cursorStyle,
      }}
    >
      <Stage
        ref={stageRef}
        width={containerSize.width}
        height={containerSize.height}
        onWheel={handleWheel}
        onDblClick={handleDoubleClick}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
      >
        {/* Drafting Grid */}
        {showGrid && (
          <CanvasGrid
            viewport={viewport}
            containerWidth={containerSize.width}
            containerHeight={containerSize.height}
          />
        )}

        {/* Floor Plan Geometry Layer */}
        <Layer>
          {renderModel && (
            <KonvaFloorPlanRenderer
              model={renderModel}
              viewport={viewport}
              selectedObjectId={selectedObjectId}
              onSelectObject={onSelectObject}
              onTransformChange={onTransformChange}
              onSnapGuidesChange={onSnapGuidesChange}
              snapGuides={snapGuides}
            />
          )}
        </Layer>

        {/* Task 6.1 & 6.2 Freehand Region Drawing & Preview Layer */}
        <Layer>
          <FreehandRegionLayer
            stroke={freehandStroke}
            regionPreview={regionPreview}
            viewport={viewport}
          />
        </Layer>
      </Stage>
    </div>
  );
};
