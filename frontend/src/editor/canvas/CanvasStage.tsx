/**
 * Konva Canvas Stage Component (Task 5.2 & Task 5.3).
 * Establishes Konva Stage & Layer hierarchy, viewport mouse wheel zoom, panning, and architectural floor plan visualization.
 * Architectural layer rendering is decoupled via RendererAdapter (KonvaFloorPlanRenderer).
 * Authoritative geometry logic is strictly isolated in Python backend.
 */

import React, { useRef, useEffect, useState, useCallback } from "react";
import { Stage, Layer } from "react-konva";
import Konva from "konva";
import { Viewport, Point2D } from "./canvasTypes";
import { CanvasGrid } from "./CanvasGrid";
import { screenToWorld, zoomAtPoint } from "./viewport";
import { FloorPlanRenderModel } from "../renderer/renderTypes";
import { KonvaFloorPlanRenderer } from "../renderer/KonvaRendererAdapter";

interface CanvasStageProps {
  viewport: Viewport;
  onViewportChange: (newViewport: Viewport) => void;
  onCursorMove?: (worldPt: Point2D) => void;
  showGrid?: boolean;
  renderModel?: FloorPlanRenderModel;
}

export const CanvasStage: React.FC<CanvasStageProps> = ({
  viewport,
  onViewportChange,
  onCursorMove,
  showGrid = true,
  renderModel,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
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
      for (const entry of entries) {
        if (entry.contentRect) {
          const width = Math.max(200, entry.contentRect.width);
          const height = Math.max(200, entry.contentRect.height);
          setContainerSize({ width, height });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Mouse wheel zoom centered at pointer location
  const handleWheel = useCallback(
    (e: Konva.KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();
      const stage = stageRef.current;
      if (!stage) return;

      const pointer = stage.getPointerPosition();
      if (!pointer) return;

      const zoomFactor = e.evt.deltaY < 0 ? 1.1 : 0.9;
      const newViewport = zoomAtPoint(pointer, zoomFactor, viewport);
      onViewportChange(newViewport);
    },
    [viewport, onViewportChange]
  );

  // Pointer move handler for coordinate updates & middle-click panning
  const handleMouseMove = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      const stage = stageRef.current;
      if (!stage) return;

      const pointer = stage.getPointerPosition();
      if (pointer && onCursorMove) {
        const worldPt = screenToWorld(pointer, viewport);
        onCursorMove(worldPt);
      }

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
    [isPanning, viewport, onViewportChange, onCursorMove]
  );

  const handleMouseDown = useCallback((e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button === 1 || e.evt.shiftKey) {
      setIsPanning(true);
      panStartRef.current = { x: e.evt.clientX, y: e.evt.clientY };
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        backgroundColor: "#0f172a",
        cursor: isPanning ? "grabbing" : "default",
      }}
    >
      <Stage
        ref={stageRef}
        width={containerSize.width}
        height={containerSize.height}
        onWheel={handleWheel}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
      >
        {/* Layer 1: Grid Layer */}
        {showGrid && (
          <CanvasGrid
            viewport={viewport}
            containerWidth={containerSize.width}
            containerHeight={containerSize.height}
          />
        )}

        {/* Layer 2: Floor Plan Geometry Layer rendered via RendererAdapter */}
        <Layer>
          {renderModel && (
            <KonvaFloorPlanRenderer model={renderModel} viewport={viewport} />
          )}
        </Layer>
      </Stage>
    </div>
  );
};
