/**
 * Konva Canvas Stage Component (Task 5.2).
 * Establishes Konva Stage & Layer hierarchy, viewport mouse wheel zoom, panning, and basic floor plan visualization.
 * Authoritative geometry logic is strictly isolated in Python backend; Konva acts solely as a renderer.
 */

import React, { useRef, useEffect, useState, useCallback } from "react";
import { Stage, Layer, Line, Rect, Arc, Group, Text } from "react-konva";
import Konva from "konva";
import { DemoRenderModel, Viewport, Point2D } from "./canvasTypes";
import { CanvasGrid } from "./CanvasGrid";
import {
  worldToScreen,
  screenToWorld,
  zoomAtPoint,
  createInitialViewport,
} from "./viewport";

interface CanvasStageProps {
  viewport: Viewport;
  onViewportChange: (newViewport: Viewport) => void;
  onCursorMove?: (worldPt: Point2D) => void;
  showGrid?: boolean;
  demoModel?: DemoRenderModel;
}

export const CanvasStage: React.FC<CanvasStageProps> = ({
  viewport,
  onViewportChange,
  onCursorMove,
  showGrid = true,
  demoModel,
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

      // Determine zoom factor: scrolling up zooms in (factor > 1), scrolling down zooms out (factor < 1)
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
    // Pan trigger: Middle mouse button (button === 1) or drag on canvas background
    if (e.evt.button === 1 || e.evt.shiftKey) {
      setIsPanning(true);
      panStartRef.current = { x: e.evt.clientX, y: e.evt.clientY };
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Compute flattened polygon points for room boundary
  const roomPointsFlat = React.useMemo(() => {
    if (!demoModel || !demoModel.boundaryPolygon) return [];
    return demoModel.boundaryPolygon.flatMap((pt) => {
      const s = worldToScreen(pt, viewport);
      return [s.x, s.y];
    });
  }, [demoModel, viewport]);

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

        {/* Layer 2: Floor Plan Geometry Layer */}
        <Layer>
          {demoModel && (
            <Group>
              {/* Room Outer Boundary Polygon */}
              {roomPointsFlat.length >= 6 && (
                <Line
                  points={roomPointsFlat}
                  closed
                  stroke="#38bdf8"
                  strokeWidth={2}
                  fill="rgba(56, 189, 248, 0.06)"
                />
              )}

              {/* Room Name Label */}
              {demoModel.boundaryPolygon && demoModel.boundaryPolygon.length > 0 && (
                <Text
                  text={`${demoModel.roomName} (Room ID: ${demoModel.roomId})`}
                  x={worldToScreen(demoModel.boundaryPolygon[0], viewport).x + 10}
                  y={worldToScreen(demoModel.boundaryPolygon[0], viewport).y + 10}
                  fill="#94a3b8"
                  fontSize={14}
                  fontFamily="Inter, sans-serif"
                />
              )}

              {/* Walls */}
              {demoModel.walls.map((wall) => {
                const sStart = worldToScreen(wall.start, viewport);
                const sEnd = worldToScreen(wall.end, viewport);
                return (
                  <Line
                    key={wall.id}
                    points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
                    stroke="#cbd5e1"
                    strokeWidth={Math.max(2, wall.thicknessMeters * viewport.scale)}
                    lineCap="round"
                  />
                );
              })}

              {/* Doors */}
              {demoModel.doors.map((door) => {
                const sPos = worldToScreen(door.position, viewport);
                const sWidth = door.widthMeters * viewport.scale;
                return (
                  <Group key={door.id} x={sPos.x} y={sPos.y}>
                    <Arc
                      angle={door.swingAngleDeg}
                      rotation={0}
                      innerRadius={0}
                      outerRadius={sWidth}
                      fill="rgba(251, 191, 36, 0.15)"
                      stroke="#f59e0b"
                      strokeWidth={1.5}
                      dash={[3, 3]}
                    />
                    <Line
                      points={[0, 0, sWidth, 0]}
                      stroke="#f59e0b"
                      strokeWidth={2}
                    />
                  </Group>
                );
              })}

              {/* Columns */}
              {demoModel.columns.map((col) => {
                const sPos = worldToScreen(col.position, viewport);
                const sW = col.widthMeters * viewport.scale;
                const sH = col.heightMeters * viewport.scale;
                return (
                  <Rect
                    key={col.id}
                    x={sPos.x - sW / 2}
                    y={sPos.y - sH / 2}
                    width={sW}
                    height={sH}
                    fill="rgba(239, 68, 68, 0.25)"
                    stroke="#ef4444"
                    strokeWidth={1.5}
                  />
                );
              })}
            </Group>
          )}
        </Layer>
      </Stage>
    </div>
  );
};
