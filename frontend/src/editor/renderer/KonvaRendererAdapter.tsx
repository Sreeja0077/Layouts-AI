/**
 * Konva Specific Implementation of RendererAdapter (Task 5.3).
 * Translates renderer-neutral architectural models into React-Konva graphic primitives.
 * Keeps Konva rendering details isolated from canonical domain geometry.
 */

import React from "react";
import { Group, Line, Rect, Arc, Text } from "react-konva";
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
import { worldToScreen } from "../canvas/viewport";

export interface KonvaRendererProps {
  model: FloorPlanRenderModel;
  viewport: Viewport;
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

/** Default singleton instance of KonvaRendererAdapter */
export const konvaRendererAdapter = new KonvaRendererAdapterImpl();

/**
 * React Component Wrapper using KonvaRendererAdapter to render a FloorPlanRenderModel.
 */
export const KonvaFloorPlanRenderer: React.FC<KonvaRendererProps> = ({ model, viewport }) => {
  return konvaRendererAdapter.renderFloorPlan(model, viewport);
};
