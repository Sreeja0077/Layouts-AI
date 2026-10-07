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
  RenderSpace,
  RenderFurniture,
  RenderGeometry,
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
  private static SPACE_COLOR_PALETTE = [
    { fill: "rgba(55, 65, 81, 0.65)", stroke: "rgba(156, 163, 175, 0.5)", text: "#e5e7eb" },    // Slate / Office
    { fill: "rgba(120, 53, 15, 0.55)", stroke: "rgba(217, 119, 6, 0.5)", text: "#fde68a" },    // Warm Wood / Exec Suite
    { fill: "rgba(30, 58, 138, 0.55)", stroke: "rgba(96, 165, 250, 0.5)", text: "#bfdbfe" },   // Deep Navy / Meeting Room
    { fill: "rgba(63, 63, 70, 0.65)", stroke: "rgba(161, 161, 170, 0.5)", text: "#f4f4f5" },   // Charcoal / Reception
    { fill: "rgba(15, 118, 110, 0.55)", stroke: "rgba(45, 212, 191, 0.5)", text: "#ccfbf1" },  // Teal / Lounge
    { fill: "rgba(124, 45, 18, 0.55)", stroke: "rgba(251, 146, 60, 0.5)", text: "#ffedd5" },   // Amber / Corridor
    { fill: "rgba(74, 4, 78, 0.55)", stroke: "rgba(192, 132, 252, 0.5)", text: "#f3e8ff" },   // Purple / Storage
  ];

  private renderPolygonGeometry(
    id: string,
    geometry: RenderGeometry,
    viewport: Viewport,
    styles: { fill?: string; stroke?: string; strokeWidth?: number; dash?: number[] }
  ): JSX.Element {
    return (
      <Group key={`geom-${id}`}>
        {geometry.polygons.map((poly, polyIdx) => {
          const extPts = poly.exterior.flatMap((pt) => {
            const s = worldToScreen(pt, viewport);
            return [s.x, s.y];
          });
          if (extPts.length < 6) return null;
          return (
            <React.Fragment key={`poly-${id}-${polyIdx}`}>
              <Line
                points={extPts}
                closed
                fill={styles.fill || "transparent"}
                stroke={styles.stroke || "#94a3b8"}
                strokeWidth={styles.strokeWidth ?? 1.5}
                dash={styles.dash}
              />
              {poly.holes?.map((hole, holeIdx) => {
                const holePts = hole.flatMap((pt) => {
                  const s = worldToScreen(pt, viewport);
                  return [s.x, s.y];
                });
                if (holePts.length < 6) return null;
                return (
                  <Line
                    key={`hole-${id}-${polyIdx}-${holeIdx}`}
                    points={holePts}
                    closed
                    fill="#000000"
                    stroke={styles.stroke || "#94a3b8"}
                    strokeWidth={styles.strokeWidth ?? 1}
                  />
                );
              })}
            </React.Fragment>
          );
        })}
      </Group>
    );
  }

  renderFloorPlan(model: Readonly<FloorPlanRenderModel>, viewport: Viewport): JSX.Element {
    return (
      <Group key={`fp-${model.id}`}>
        {/* Architectural Layers */}
        {this.renderSpaces(model.spaces || [], viewport)}
        {this.renderWalls(model.walls, viewport)}
        {this.renderWindows(model.windows, viewport)}
        {this.renderDoors(model.doors, viewport)}
        {this.renderColumns(model.columns, viewport)}
        {this.renderFurniture(model.furniture, viewport)}
      </Group>
    );
  }

  renderSpaces(spaces: ReadonlyArray<RenderSpace>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-spaces">
        {spaces.map((space, idx) => {
          if (!space.geometry) return null;
          const style = KonvaRendererAdapterImpl.SPACE_COLOR_PALETTE[
            idx % KonvaRendererAdapterImpl.SPACE_COLOR_PALETTE.length
          ];

          let centroidScreen = { x: 0, y: 0 };
          const firstPoly = space.geometry.polygons[0];
          if (firstPoly && firstPoly.exterior.length > 0) {
            const sumX = firstPoly.exterior.reduce((acc, pt) => acc + pt.x, 0);
            const sumY = firstPoly.exterior.reduce((acc, pt) => acc + pt.y, 0);
            const worldCentroid = {
              x: sumX / firstPoly.exterior.length,
              y: sumY / firstPoly.exterior.length,
            };
            centroidScreen = worldToScreen(worldCentroid, viewport);
          }

          return (
            <Group key={`space-grp-${space.id || idx}`}>
              {this.renderPolygonGeometry(space.id, space.geometry, viewport, {
                fill: style.fill,
                stroke: style.stroke,
                strokeWidth: 1.5,
              })}
              {firstPoly && firstPoly.exterior.length > 0 && (
                <Text
                  text={space.name || `Space ${idx + 1}`}
                  x={centroidScreen.x - 50}
                  y={centroidScreen.y - 8}
                  width={100}
                  align="center"
                  fontSize={Math.max(10, Math.min(13, 0.45 * viewport.scale))}
                  fill={style.text}
                  fontFamily="Inter, sans-serif"
                  fontStyle="bold"
                  opacity={0.85}
                  listening={false}
                />
              )}
            </Group>
          );
        })}
      </Group>
    );
  }

  renderWalls(walls: ReadonlyArray<RenderWall>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-walls">
        {walls.map((wall) => {
          if (wall.geometry) {
            return this.renderPolygonGeometry(wall.id, wall.geometry, viewport, {
              fill: "#27272a",
              stroke: "#e2e8f0",
              strokeWidth: 1.5,
            });
          }
          if (wall.start && wall.end) {
            const sStart = worldToScreen(wall.start, viewport);
            const sEnd = worldToScreen(wall.end, viewport);
            return (
              <Line
                key={`wall-${wall.id}`}
                points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
                stroke="#cbd5e1"
                strokeWidth={Math.max(4, wall.thicknessMeters * viewport.scale)}
                lineCap="round"
              />
            );
          }
          return null;
        })}
      </Group>
    );
  }

  renderDoors(doors: ReadonlyArray<RenderDoor>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-doors">
        {doors.map((door) => {
          if (door.geometry) {
            return this.renderPolygonGeometry(door.id, door.geometry, viewport, {
              fill: "rgba(37, 99, 235, 0.75)",
              stroke: "#60a5fa",
              strokeWidth: 2,
            });
          }
          if (door.position) {
            const sPos = worldToScreen(door.position, viewport);
            const sWidth = Math.min(door.widthMeters * viewport.scale, 28);
            const swingAngle = door.swingAngleDeg ?? 90;
            const rotation = door.rotationDeg ?? 0;
            return (
              <Group key={`door-${door.id}`} x={sPos.x} y={sPos.y} rotation={rotation}>
                <Arc
                  angle={swingAngle}
                  rotation={0}
                  innerRadius={0}
                  outerRadius={sWidth}
                  fill="rgba(59, 130, 246, 0.3)"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dash={[3, 3]}
                />
                <Line points={[0, 0, sWidth, 0]} stroke="#60a5fa" strokeWidth={2.5} />
              </Group>
            );
          }
          return null;
        })}
      </Group>
    );
  }

  renderWindows(windows: ReadonlyArray<RenderWindow>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-windows">
        {windows.map((win) => {
          if (win.geometry) {
            return this.renderPolygonGeometry(win.id, win.geometry, viewport, {
              fill: "rgba(6, 182, 212, 0.6)",
              stroke: "#22d3ee",
              strokeWidth: 2,
            });
          }
          if (win.start && win.end) {
            const sStart = worldToScreen(win.start, viewport);
            const sEnd = worldToScreen(win.end, viewport);
            return (
              <Line
                key={`win-${win.id}`}
                points={[sStart.x, sStart.y, sEnd.x, sEnd.y]}
                stroke="#00f0ff"
                strokeWidth={Math.max(4, (win.thicknessMeters || 0.15) * viewport.scale)}
                lineCap="square"
              />
            );
          }
          return null;
        })}
      </Group>
    );
  }

  renderColumns(columns: ReadonlyArray<RenderColumn>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-columns">
        {columns.map((col) => {
          if (col.geometry) {
            return this.renderPolygonGeometry(col.id, col.geometry, viewport, {
              fill: "#f59e0b",
              stroke: "#fde047",
              strokeWidth: 2,
            });
          }
          if (col.position) {
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
                fill="#f59e0b"
                stroke="#fde047"
                strokeWidth={2}
                cornerRadius={1}
              />
            );
          }
          return null;
        })}
      </Group>
    );
  }

  renderFurniture(furniture: ReadonlyArray<RenderFurniture>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-furniture">
        {furniture.map((item) => {
          const subtype = (item.subtype || item.itemType || "OTHER").toUpperCase();
          const sourceIfcType = (item.sourceIfcType || "").toUpperCase();

          if (subtype === "DOOR" || sourceIfcType === "IFCDOOR") {
            if (item.geometry) {
              return this.renderDoorPlanSymbol(item, viewport);
            }
          }
          if (subtype === "WINDOW" || sourceIfcType === "IFCWINDOW") {
            if (item.geometry) {
              return this.renderWindowPlanSymbol(item, viewport);
            }
          }
          if (subtype === "CHAIR") {
            return this.renderChairPlanSymbol(item, viewport);
          }
          if (subtype === "TABLE") {
            return this.renderTablePlanSymbol(item, viewport);
          }
          if (subtype === "DESK") {
            return this.renderDeskPlanSymbol(item, viewport);
          }
          if (subtype === "CABINET" || subtype === "STORAGE") {
            return this.renderCabinetPlanSymbol(item, viewport);
          }
          if (subtype === "SOFA") {
            return this.renderSofaPlanSymbol(item, viewport);
          }
          if (subtype === "SANITARY") {
            return this.renderSanitaryPlanSymbol(item, viewport);
          }
          if (subtype === "EQUIPMENT" || subtype === "FIXTURE") {
            return this.renderEquipmentPlanSymbol(item, viewport);
          }

          return this.renderGenericFurnitureSymbol(item, viewport);
        })}
      </Group>
    );
  }

  private renderDoorPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(37, 99, 235, 0.75)",
        stroke: "#60a5fa",
        strokeWidth: 2,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = Math.min(item.widthMeters * viewport.scale, 28);
    return (
      <Group key={`door-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
        <Arc angle={90} rotation={0} innerRadius={0} outerRadius={sW} fill="rgba(59, 130, 246, 0.3)" stroke="#3b82f6" strokeWidth={2} dash={[3, 3]} />
        <Line points={[0, 0, sW, 0]} stroke="#60a5fa" strokeWidth={2.5} />
      </Group>
    );
  }

  private renderWindowPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(6, 182, 212, 0.6)",
        stroke: "#22d3ee",
        strokeWidth: 2,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = (item.depthMeters || 0.2) * viewport.scale;
    return (
      <Rect key={`win-sym-${item.id}`} x={sPos.x - sW / 2} y={sPos.y - sD / 2} width={sW} height={sD} fill="rgba(6, 182, 212, 0.6)" stroke="#22d3ee" strokeWidth={2} />
    );
  }

  private renderChairPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(217, 119, 6, 0.75)",
        stroke: "#fbbf24",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`chair-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(217, 119, 6, 0.75)" stroke="#fbbf24" strokeWidth={1.5} cornerRadius={3} />
        <Line points={[-sW / 2 + 2, -sD / 2 + 2, sW / 2 - 2, -sD / 2 + 2]} stroke="#fef08a" strokeWidth={2} />
      </Group>
    );
  }

  private renderTablePlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(180, 83, 9, 0.7)",
        stroke: "#f59e0b",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`tbl-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(180, 83, 9, 0.7)" stroke="#f59e0b" strokeWidth={1.5} cornerRadius={2} />
      </Group>
    );
  }

  private renderDeskPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(180, 83, 9, 0.75)",
        stroke: "#f59e0b",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`desk-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(180, 83, 9, 0.75)" stroke="#f59e0b" strokeWidth={1.5} cornerRadius={2} />
      </Group>
    );
  }

  private renderCabinetPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(71, 85, 105, 0.7)",
        stroke: "#94a3b8",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`cab-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(71, 85, 105, 0.7)" stroke="#94a3b8" strokeWidth={1.5} cornerRadius={1} />
      </Group>
    );
  }

  private renderSofaPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(99, 102, 241, 0.7)",
        stroke: "#818cf8",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`sofa-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(99, 102, 241, 0.7)" stroke="#818cf8" strokeWidth={1.5} cornerRadius={4} />
      </Group>
    );
  }

  private renderSanitaryPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(14, 116, 144, 0.7)",
        stroke: "#06b6d4",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`san-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(14, 116, 144, 0.7)" stroke="#06b6d4" strokeWidth={1.5} cornerRadius={4} />
      </Group>
    );
  }

  private renderEquipmentPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(15, 118, 110, 0.7)",
        stroke: "#14b8a6",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`eq-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(15, 118, 110, 0.7)" stroke="#14b8a6" strokeWidth={1.5} cornerRadius={1} />
      </Group>
    );
  }

  private renderGenericFurnitureSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(180, 83, 9, 0.65)",
        stroke: "#f59e0b",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`gen-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="rgba(180, 83, 9, 0.65)" stroke="#f59e0b" strokeWidth={1.5} cornerRadius={2} />
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

      {/* Architectural Layers rendered via konvaRendererAdapter */}
      {konvaRendererAdapter.renderFloorPlan(model, viewport)}

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
