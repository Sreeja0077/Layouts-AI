/**
 * Konva Specific Implementation of RendererAdapter (Task 5.3 & Task 5.4).
 * Translates renderer-neutral architectural models into React-Konva graphic primitives.
 * Provides interactive Konva Transformer, object selection highlights, and snap guide visualization.
 */

import React, { useRef, useEffect } from "react";
import { Group, Line, Rect, Arc, Text, Transformer } from "react-konva";
import Konva from "konva";
import {
  FloorPlanRenderModel,
  RenderWall,
  RenderDoor,
  RenderWindow,
  RenderColumn,
  RenderFurniture,
} from "./renderTypes";
import { RendererAdapter } from "./RendererAdapter";
import { Viewport } from "../canvas/canvasTypes";
import { worldToScreen, screenToWorld } from "../canvas/viewport";
import { SnapGuideLine } from "../snapping/snappingTypes";
import { TransformChange, MIN_FURNITURE_DIMENSION_METERS } from "../transforms/transformTypes";
import { calculateSnap } from "../snapping/snapper";

export interface KonvaRendererProps {
  model: FloorPlanRenderModel;
  viewport: Viewport;
  selectedObjectId?: string | null;
  onSelectObject?: (id: string | null) => void;
  onTransformChange?: (change: TransformChange) => void;
  onSnapGuidesChange?: (guides: SnapGuideLine[]) => void;
  snapGuides?: SnapGuideLine[];
}

/**
 * Konva implementation of the RendererAdapter interface.
 */
export class KonvaRendererAdapterImpl implements RendererAdapter<JSX.Element> {
  renderFloorPlan(model: Readonly<FloorPlanRenderModel>, viewport: Viewport): JSX.Element {
    const boundaryPointsFlat = model.boundary.flatMap((pt) => {
      const s = worldToScreen(pt, viewport);
      return [s.x, s.y];
    });

    return (
      <Group key={`fp-${model.id}`}>
        {/* Room Outer Boundary */}
        {boundaryPointsFlat.length >= 6 && (
          <Line
            points={boundaryPointsFlat}
            closed
            stroke="#38bdf8"
            strokeWidth={2}
            fill="rgba(56, 189, 248, 0.06)"
          />
        )}

        {/* Room Name Label */}
        {model.name && model.boundary.length > 0 && (
          <Text
            text={`${model.name} (${model.id})`}
            x={worldToScreen(model.boundary[0], viewport).x + 10}
            y={worldToScreen(model.boundary[0], viewport).y + 10}
            fill="#94a3b8"
            fontSize={14}
            fontFamily="Inter, sans-serif"
          />
        )}

        {/* Architectural Layers */}
        {this.renderWalls(model.walls, viewport)}
        {this.renderWindows(model.windows, viewport)}
        {this.renderDoors(model.doors, viewport)}
        {this.renderColumns(model.columns, viewport)}
        {this.renderFurniture(model.furniture, viewport)}
      </Group>
    );
  }

  renderWalls(walls: ReadonlyArray<RenderWall>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-walls">
        {walls.map((wall) => {
          const sStart = worldToScreen(wall.start, viewport);
          const sEnd = worldToScreen(wall.end, viewport);
          return (
            <Line
              key={`wall-${wall.id}`}
              points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
              stroke={wall.isExterior ? "#f1f5f9" : "#cbd5e1"}
              strokeWidth={Math.max(2, wall.thicknessMeters * viewport.scale)}
              lineCap="round"
            />
          );
        })}
      </Group>
    );
  }

  renderDoors(doors: ReadonlyArray<RenderDoor>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-doors">
        {doors.map((door) => {
          const sPos = worldToScreen(door.position, viewport);
          const sWidth = door.widthMeters * viewport.scale;
          const swingAngle = door.swingAngleDeg ?? 90;
          const rotation = door.rotationDeg ?? 0;
          return (
            <Group key={`door-${door.id}`} x={sPos.x} y={sPos.y} rotation={rotation}>
              <Arc
                angle={swingAngle}
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
      </Group>
    );
  }

  renderWindows(windows: ReadonlyArray<RenderWindow>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-windows">
        {windows.map((win) => {
          const sStart = worldToScreen(win.start, viewport);
          const sEnd = worldToScreen(win.end, viewport);
          return (
            <Line
              key={`win-${win.id}`}
              points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
              stroke="#38bdf8"
              strokeWidth={Math.max(3, (win.thicknessMeters || 0.15) * viewport.scale)}
              dash={[4, 4]}
              lineCap="square"
            />
          );
        })}
      </Group>
    );
  }

  renderColumns(columns: ReadonlyArray<RenderColumn>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-columns">
        {columns.map((col) => {
          const sPos = worldToScreen(col.position, viewport);
          const sW = col.widthMeters * viewport.scale;
          const sH = col.heightMeters * viewport.scale;
          return (
            <Rect
              key={`col-${col.id}`}
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
    );
  }

  renderFurniture(furniture: ReadonlyArray<RenderFurniture>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-furniture">
        {furniture.map((item) => {
          const sPos = worldToScreen(item.position, viewport);
          const sW = item.widthMeters * viewport.scale;
          const sD = item.depthMeters * viewport.scale;
          return (
            <Group key={`furn-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
              <Rect
                x={-sW / 2}
                y={-sD / 2}
                width={sW}
                height={sD}
                fill={item.isLocked ? "rgba(148, 163, 184, 0.3)" : "rgba(99, 102, 241, 0.25)"}
                stroke={item.isLocked ? "#94a3b8" : "#6366f1"}
                strokeWidth={1.5}
                cornerRadius={2}
              />
              <Text
                text={item.itemType}
                x={-sW / 2 + 2}
                y={-sD / 2 + 2}
                fontSize={Math.max(10, Math.min(12, sW / 4))}
                fill="#e2e8f0"
                fontFamily="Inter, sans-serif"
              />
            </Group>
          );
        })}
      </Group>
    );
  }

  clear(): void {
    // No-op for React declaration pattern
  }
}

export const konvaRendererAdapter = new KonvaRendererAdapterImpl();

/**
 * Interactive React Component Wrapper using KonvaRendererAdapter to render FloorPlanRenderModel.
 * Features selectable items, Konva Transformer for drag/rotate/resize, locked item guards, and snap guides.
 */
export const KonvaFloorPlanRenderer: React.FC<KonvaRendererProps> = ({
  model,
  viewport,
  selectedObjectId,
  onSelectObject,
  onTransformChange,
  onSnapGuidesChange,
  snapGuides = [],
}) => {
  const transformerRef = useRef<Konva.Transformer>(null);
  const selectedNodeRef = useRef<Konva.Group | Konva.Shape | null>(null);

  // Attach Transformer to selected node
  useEffect(() => {
    const tr = transformerRef.current;
    if (!tr) return;

    if (selectedNodeRef.current && selectedObjectId) {
      const selectedItem = model.furniture.find((f) => f.id === selectedObjectId);
      // Attach transformer only if selected furniture exists and is not locked
      if (selectedItem && !selectedItem.isLocked) {
        tr.nodes([selectedNodeRef.current]);
        tr.getLayer()?.batchDraw();
      } else {
        tr.nodes([]);
        tr.getLayer()?.batchDraw();
      }
    } else {
      tr.nodes([]);
      tr.getLayer()?.batchDraw();
    }
  }, [selectedObjectId, model, viewport]);

  const boundaryPointsFlat = model.boundary.flatMap((pt) => {
    const s = worldToScreen(pt, viewport);
    return [s.x, s.y];
  });

  return (
    <Group>
      {/* Snap Guide Lines Layer */}
      {snapGuides.map((guide) => {
        const p1 = worldToScreen(guide.startMeters, viewport);
        const p2 = worldToScreen(guide.endMeters, viewport);
        return (
          <Line
            key={guide.id}
            points={[p1.x, p1.y, p2.x, p2.y]}
            stroke="#38bdf8"
            strokeWidth={1}
            dash={[4, 4]}
          />
        );
      })}

      {/* Room Outer Boundary */}
      {boundaryPointsFlat.length >= 6 && (
        <Line
          points={boundaryPointsFlat}
          closed
          stroke="#38bdf8"
          strokeWidth={2}
          fill="rgba(56, 189, 248, 0.06)"
          listening={false}
        />
      )}

      {/* Room Name Label */}
      {model.name && model.boundary.length > 0 && (
        <Text
          text={`${model.name} (${model.id})`}
          x={worldToScreen(model.boundary[0], viewport).x + 10}
          y={worldToScreen(model.boundary[0], viewport).y + 10}
          fill="#94a3b8"
          fontSize={14}
          fontFamily="Inter, sans-serif"
          listening={false}
        />
      )}

      {/* Architectural Walls */}
      <Group key="layer-walls">
        {model.walls.map((wall) => {
          const sStart = worldToScreen(wall.start, viewport);
          const sEnd = worldToScreen(wall.end, viewport);
          const isSelected = selectedObjectId === wall.id;
          return (
            <Line
              key={`wall-${wall.id}`}
              points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
              stroke={isSelected ? "#38bdf8" : wall.isExterior ? "#f1f5f9" : "#cbd5e1"}
              strokeWidth={Math.max(2, wall.thicknessMeters * viewport.scale) + (isSelected ? 2 : 0)}
              lineCap="round"
              onClick={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(wall.id);
              }}
              onTap={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(wall.id);
              }}
            />
          );
        })}
      </Group>

      {/* Windows */}
      <Group key="layer-windows">
        {model.windows.map((win) => {
          const sStart = worldToScreen(win.start, viewport);
          const sEnd = worldToScreen(win.end, viewport);
          const isSelected = selectedObjectId === win.id;
          return (
            <Line
              key={`win-${win.id}`}
              points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
              stroke={isSelected ? "#38bdf8" : "#38bdf8"}
              strokeWidth={Math.max(3, (win.thicknessMeters || 0.15) * viewport.scale) + (isSelected ? 2 : 0)}
              dash={[4, 4]}
              lineCap="square"
              onClick={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(win.id);
              }}
              onTap={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(win.id);
              }}
            />
          );
        })}
      </Group>

      {/* Doors */}
      <Group key="layer-doors">
        {model.doors.map((door) => {
          const sPos = worldToScreen(door.position, viewport);
          const sWidth = door.widthMeters * viewport.scale;
          const swingAngle = door.swingAngleDeg ?? 90;
          const rotation = door.rotationDeg ?? 0;
          const isSelected = selectedObjectId === door.id;
          return (
            <Group
              key={`door-${door.id}`}
              x={sPos.x}
              y={sPos.y}
              rotation={rotation}
              onClick={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(door.id);
              }}
              onTap={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(door.id);
              }}
            >
              <Arc
                angle={swingAngle}
                rotation={0}
                innerRadius={0}
                outerRadius={sWidth}
                fill="rgba(251, 191, 36, 0.15)"
                stroke={isSelected ? "#38bdf8" : "#f59e0b"}
                strokeWidth={isSelected ? 2.5 : 1.5}
                dash={[3, 3]}
              />
              <Line
                points={[0, 0, sWidth, 0]}
                stroke={isSelected ? "#38bdf8" : "#f59e0b"}
                strokeWidth={isSelected ? 3 : 2}
              />
            </Group>
          );
        })}
      </Group>

      {/* Columns */}
      <Group key="layer-columns">
        {model.columns.map((col) => {
          const sPos = worldToScreen(col.position, viewport);
          const sW = col.widthMeters * viewport.scale;
          const sH = col.heightMeters * viewport.scale;
          const isSelected = selectedObjectId === col.id;
          return (
            <Rect
              key={`col-${col.id}`}
              x={sPos.x - sW / 2}
              y={sPos.y - sH / 2}
              width={sW}
              height={sH}
              fill="rgba(239, 68, 68, 0.25)"
              stroke={isSelected ? "#38bdf8" : "#ef4444"}
              strokeWidth={isSelected ? 3 : 1.5}
              onClick={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(col.id);
              }}
              onTap={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(col.id);
              }}
            />
          );
        })}
      </Group>

      {/* Furniture Layer */}
      <Group key="layer-furniture">
        {model.furniture.map((item) => {
          const sPos = worldToScreen(item.position, viewport);
          const sW = item.widthMeters * viewport.scale;
          const sD = item.depthMeters * viewport.scale;
          const isSelected = selectedObjectId === item.id;
          const isEditable = !item.isLocked;

          return (
            <Group
              key={`furn-${item.id}`}
              ref={(node) => {
                if (isSelected && isEditable) {
                  selectedNodeRef.current = node;
                }
              }}
              x={sPos.x}
              y={sPos.y}
              rotation={item.rotationDeg}
              draggable={isEditable}
              onClick={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(item.id);
              }}
              onTap={(e) => {
                e.cancelBubble = true;
                onSelectObject?.(item.id);
              }}
              onDragMove={(e) => {
                if (!isEditable) return;

                // Screen position of current node during drag
                const nodeScreenPos = { x: e.target.x(), y: e.target.y() };
                const worldPosRaw = screenToWorld(nodeScreenPos, viewport);

                // Compute grid & alignment snapping in world units
                const snapRes = calculateSnap(worldPosRaw, item.id, model);

                // Convert snapped world position back to screen position for visual feedback
                const snappedScreen = worldToScreen(snapRes.snappedPosition, viewport);
                e.target.x(snappedScreen.x);
                e.target.y(snappedScreen.y);

                onSnapGuidesChange?.(snapRes.activeGuides);

                // Emit draft position update
                onTransformChange?.({
                  objectId: item.id,
                  newPosition: snapRes.snappedPosition,
                });
              }}
              onDragEnd={(e) => {
                if (!isEditable) return;
                onSnapGuidesChange?.([]);
                const finalScreenPos = { x: e.target.x(), y: e.target.y() };
                const finalWorldPos = screenToWorld(finalScreenPos, viewport);
                const snapRes = calculateSnap(finalWorldPos, item.id, model);

                onTransformChange?.({
                  objectId: item.id,
                  newPosition: snapRes.snappedPosition,
                });
              }}
              onTransformEnd={(e) => {
                if (!isEditable) return;
                const node = e.target;
                const scaleX = node.scaleX();
                const scaleY = node.scaleY();
                const rotation = node.rotation();

                // Reset visual scale factor on node
                node.scaleX(1);
                node.scaleY(1);

                // Calculate updated logical world dimensions in meters
                const newWidthMeters = Math.max(
                  MIN_FURNITURE_DIMENSION_METERS,
                  (sW * scaleX) / viewport.scale
                );
                const newDepthMeters = Math.max(
                  MIN_FURNITURE_DIMENSION_METERS,
                  (sD * scaleY) / viewport.scale
                );

                const nodeScreenPos = { x: node.x(), y: node.y() };
                const newPosition = screenToWorld(nodeScreenPos, viewport);

                onTransformChange?.({
                  objectId: item.id,
                  newPosition,
                  newRotationDeg: Math.round(rotation),
                  newWidthMeters,
                  newDepthMeters,
                });
              }}
            >
              {/* Highlight selection rectangle */}
              <Rect
                x={-sW / 2}
                y={-sD / 2}
                width={sW}
                height={sD}
                fill={
                  item.isLocked
                    ? "rgba(148, 163, 184, 0.3)"
                    : isSelected
                    ? "rgba(56, 189, 248, 0.3)"
                    : "rgba(99, 102, 241, 0.25)"
                }
                stroke={isSelected ? "#38bdf8" : item.isLocked ? "#94a3b8" : "#6366f1"}
                strokeWidth={isSelected ? 2.5 : 1.5}
                dash={item.isLocked ? [4, 4] : undefined}
                cornerRadius={2}
              />
              <Text
                text={item.isLocked ? `🔒 ${item.itemType}` : item.itemType}
                x={-sW / 2 + 2}
                y={-sD / 2 + 2}
                fontSize={Math.max(10, Math.min(12, sW / 4))}
                fill={isSelected ? "#ffffff" : "#e2e8f0"}
                fontFamily="Inter, sans-serif"
                listening={false}
              />
            </Group>
          );
        })}
      </Group>

      {/* Konva Transformer Node for Active Selection */}
      <Transformer
        ref={transformerRef}
        rotateEnabled
        resizeEnabled
        keepRatio={false}
        borderStroke="#38bdf8"
        anchorStroke="#0284c7"
        anchorFill="#38bdf8"
        anchorSize={8}
        boundBoxFunc={(oldBox, newBox) => {
          // Guard minimum screen dimension during resize
          if (Math.abs(newBox.width) < 10 || Math.abs(newBox.height) < 10) {
            return oldBox;
          }
          return newBox;
        }}
      />
    </Group>
  );
};
