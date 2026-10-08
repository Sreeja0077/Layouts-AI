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
  RenderPoint,
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
import { extractOrientedBounds } from "./geometryUtils";
import { renderCadDoorSymbol } from "./doorSymbols";
import { renderCadGarageDoorSymbol } from "./garageDoorSymbols";
import { renderFurnitureItem } from "./furnitureSymbols";

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
    { fill: "rgba(255, 255, 255, 0.0)", stroke: "#AAAAAA", text: "#111827" },
    { fill: "rgba(255, 255, 255, 0.0)", stroke: "#AAAAAA", text: "#111827" },
    { fill: "rgba(255, 255, 255, 0.0)", stroke: "#AAAAAA", text: "#111827" },
    { fill: "rgba(255, 255, 255, 0.0)", stroke: "#AAAAAA", text: "#111827" },
  ];

  private extractOrientedBounds(geometry?: RenderGeometry): {
    pos: RenderPoint;
    width: number;
    depth: number;
    rotation: number;
  } {
    if (!geometry || !geometry.polygons || geometry.polygons.length === 0) {
      return { pos: { x: 0, y: 0 }, width: 0.9, depth: 0.15, rotation: 0 };
    }
    const pts = geometry.polygons[0].exterior;
    if (!pts || pts.length < 3) {
      return { pos: { x: 0, y: 0 }, width: 0.9, depth: 0.15, rotation: 0 };
    }

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    let maxEdgeLenSq = 0;
    let maxEdgeAngle = 0;

    for (let i = 0; i < pts.length - 1; i++) {
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const edx = p2.x - p1.x;
      const edy = p2.y - p1.y;
      const lenSq = edx * edx + edy * edy;
      if (lenSq > maxEdgeLenSq) {
        maxEdgeLenSq = lenSq;
        maxEdgeAngle = (Math.atan2(edy, edx) * 180) / Math.PI;
      }
      if (p1.x < minX) minX = p1.x;
      if (p1.x > maxX) maxX = p1.x;
      if (p1.y < minY) minY = p1.y;
      if (p1.y > maxY) maxY = p1.y;
    }

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const dx = maxX - minX;
    const dy = maxY - minY;
    let width = Math.sqrt(maxEdgeLenSq);
    if (width < 0.4) width = Math.max(dx, dy);
    let depth = Math.min(dx, dy);

    if (width < 0.3) width = 0.9;
    if (depth < 0.05) depth = 0.15;

    let rotation = maxEdgeAngle % 180;
    if (rotation < 0) rotation += 180;

    return { pos: { x: cx, y: cy }, width, depth, rotation };
  }

  private getPolygonMetrics(exterior: RenderPoint[]): { area: number; centroid: RenderPoint } {
    if (!exterior || exterior.length < 3) {
      return { area: 0, centroid: { x: 0, y: 0 } };
    }
    let pts = [...exterior];
    if (pts.length > 3 && pts[0].x === pts[pts.length - 1].x && pts[0].y === pts[pts.length - 1].y) {
      pts.pop();
    }
    const n = pts.length;
    if (n < 3) return { area: 0, centroid: pts[0] || { x: 0, y: 0 } };

    let signedArea = 0;
    let cx = 0;
    let cy = 0;
    for (let i = 0; i < n; i++) {
      const pt1 = pts[i];
      const pt2 = pts[(i + 1) % n];
      const cross = pt1.x * pt2.y - pt2.x * pt1.y;
      signedArea += cross;
      cx += (pt1.x + pt2.x) * cross;
      cy += (pt1.y + pt2.y) * cross;
    }
    signedArea = signedArea / 2;
    const absArea = Math.abs(signedArea);

    if (absArea > 0.0001 && signedArea !== 0) {
      cx = cx / (6 * signedArea);
      cy = cy / (6 * signedArea);
    } else {
      cx = pts.reduce((s, p) => s + p.x, 0) / n;
      cy = pts.reduce((s, p) => s + p.y, 0) / n;
    }
    return { area: absArea, centroid: { x: cx, y: cy } };
  }

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
        {this.renderDoors(model.doors, viewport, model.spaces || [], model.walls || [])}
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

          const firstPoly = space.geometry.polygons[0];
          if (!firstPoly || firstPoly.exterior.length < 3) return null;

          const { area, centroid } = this.getPolygonMetrics(firstPoly.exterior);
          const centroidScreen = worldToScreen(centroid, viewport);

          let rawName = (space.name || "").trim();
          if (!rawName || /^ifcspace/i.test(rawName) || /^polygon$/i.test(rawName) || /^multipolygon$/i.test(rawName)) {
            rawName = `Room ${idx + 1}`;
          }

          const areaSqm = area;
          const areaSqFt = Math.round(areaSqm * 10.7639);

          return (
            <Group key={`space-grp-${space.id || idx}`}>
              {this.renderPolygonGeometry(space.id, space.geometry, viewport, {
                fill: style.fill,
                stroke: style.stroke,
                strokeWidth: 1.5,
              })}

              {/* Clean Subtle Architectural Room Label without opaque card box */}
              <Group x={centroidScreen.x} y={centroidScreen.y} listening={false}>
                <Text
                  text={rawName}
                  x={-40}
                  y={-8}
                  width={80}
                  align="center"
                  fontSize={10}
                  fontStyle="bold"
                  fill="#334155"
                  fontFamily="Inter, sans-serif"
                  listening={false}
                />
                <Text
                  text={`${areaSqm.toFixed(1)} m²`}
                  x={-40}
                  y={4}
                  width={80}
                  align="center"
                  fontSize={8}
                  fill="#64748b"
                  fontFamily="Inter, sans-serif"
                  listening={false}
                />
              </Group>
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
              fill: "#111111",
              stroke: "#111111",
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
                stroke="#111111"
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

  renderDoors(
    doors: ReadonlyArray<RenderDoor>,
    viewport: Viewport,
    spaces: ReadonlyArray<RenderSpace> = [],
    walls: ReadonlyArray<RenderWall> = []
  ): JSX.Element {
    return (
      <Group key="layer-doors">
        {doors.map((door) => {
          let bounds = {
            pos: door.position,
            width: door.widthMeters || 0.9,
            depth: 0.15,
            rotation: door.rotationDeg || 0,
          };
          if (door.geometry) {
            bounds = extractOrientedBounds(door.geometry);
          }
          const isGarage =
            door.isGarageDoor ||
            door.subtype === "GARAGE_DOOR" ||
            door.subtype === "OVERHEAD_DOOR" ||
            door.subtype === "ROLLING_DOOR";

          if (isGarage) {
            return renderCadGarageDoorSymbol(
              door.id,
              bounds.pos,
              bounds.width,
              bounds.depth,
              bounds.rotation,
              viewport,
              spaces,
              walls
            );
          }

          return renderCadDoorSymbol(
            door.id,
            bounds.pos,
            bounds.width,
            bounds.depth,
            bounds.rotation,
            viewport,
            spaces,
            walls
          );
        })}
      </Group>
    );
  }

  renderWindows(windows: ReadonlyArray<RenderWindow>, viewport: Viewport): JSX.Element {
    return (
      <Group key="layer-windows">
        {windows.map((win) => {
          let bounds = {
            pos: win.start && win.end ? { x: (win.start.x + win.end.x) / 2, y: (win.start.y + win.end.y) / 2 } : { x: 0, y: 0 },
            width: win.start && win.end ? Math.hypot(win.end.x - win.start.x, win.end.y - win.start.y) : 1.2,
            depth: win.thicknessMeters || 0.15,
            rotation: win.start && win.end ? (Math.atan2(win.end.y - win.start.y, win.end.x - win.start.x) * 180) / Math.PI : 0,
          };
          if (win.geometry) {
            bounds = extractOrientedBounds(win.geometry);
          }
          return this.renderCadWindowSymbol(win.id, bounds.pos, bounds.width, bounds.depth, bounds.rotation, viewport);
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
              fill: "#1F1F1F",
              stroke: "#111111",
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
                fill="#1F1F1F"
                stroke="#111111"
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
        {furniture.map((item) => renderFurnitureItem(item, viewport))}
      </Group>
    );
  }

  private renderCadDoorSymbol(
    id: string,
    pos: RenderPoint,
    widthMeters: number,
    depthMeters: number,
    rotationDeg: number,
    viewport: Viewport
  ): JSX.Element {
    const sPos = worldToScreen(pos, viewport);
    const sW = Math.max(12, widthMeters * viewport.scale);
    const sD = Math.max(4, depthMeters * viewport.scale);

    return (
      <Group key={`door-cad-${id}`} x={sPos.x} y={sPos.y} rotation={rotationDeg}>
        {/* Wall opening gap — white to cut through wall fill */}
        <Rect
          x={-sW / 2}
          y={-sD / 2}
          width={sW}
          height={sD}
          fill="#FFFFFF"
          stroke="rgba(80,80,80,0.3)"
          strokeWidth={0.5}
        />
        {/* Left Wall Jamb */}
        <Line
          points={[-sW / 2, -sD / 2 - 2, -sW / 2, sD / 2 + 2]}
          stroke="#222222"
          strokeWidth={1.5}
        />
        {/* Right Wall Jamb */}
        <Line
          points={[sW / 2, -sD / 2 - 2, sW / 2, sD / 2 + 2]}
          stroke="#222222"
          strokeWidth={1.5}
        />
        {/* 90-degree Door Swing Arc */}
        <Arc
          x={-sW / 2}
          y={0}
          innerRadius={0}
          outerRadius={sW}
          angle={90}
          rotation={-90}
          fill="rgba(0, 0, 0, 0.04)"
          stroke="#555555"
          strokeWidth={1}
          dash={[4, 4]}
        />
        {/* Single Door Leaf Line attached to Hinge */}
        <Line
          points={[-sW / 2, 0, -sW / 2, -sW]}
          stroke="#111111"
          strokeWidth={2}
          lineCap="round"
        />
      </Group>
    );
  }

  private renderCadWindowSymbol(
    id: string,
    pos: RenderPoint,
    widthMeters: number,
    depthMeters: number,
    rotationDeg: number,
    viewport: Viewport
  ): JSX.Element {
    const sPos = worldToScreen(pos, viewport);
    const sW = Math.max(12, widthMeters * viewport.scale);
    const sD = Math.max(4, depthMeters * viewport.scale);

    return (
      <Group key={`win-cad-${id}`} x={sPos.x} y={sPos.y} rotation={rotationDeg}>
        {/* Opening gap — white */}
        <Rect
          x={-sW / 2}
          y={-sD / 2}
          width={sW}
          height={sD}
          fill="#FFFFFF"
          stroke="#333333"
          strokeWidth={1.5}
        />
        {/* Inner frame line — top */}
        <Line
          points={[-sW / 2, -sD / 4, sW / 2, -sD / 4]}
          stroke="#333333"
          strokeWidth={1}
        />
        {/* Inner frame line — bottom */}
        <Line
          points={[-sW / 2, sD / 4, sW / 2, sD / 4]}
          stroke="#333333"
          strokeWidth={1}
        />
        {/* Glazing center line */}
        <Line
          points={[-sW / 2, 0, sW / 2, 0]}
          stroke="#888888"
          strokeWidth={0.75}
          dash={[3, 3]}
        />
      </Group>
    );
  }

  private renderStairPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    let bounds = { pos: item.position, width: item.widthMeters, depth: item.depthMeters, rotation: item.rotationDeg || 0 };
    if (item.geometry) {
      bounds = this.extractOrientedBounds(item.geometry);
    }
    const sPos = worldToScreen(bounds.pos, viewport);
    const sW = Math.max(20, bounds.width * viewport.scale);
    const sD = Math.max(20, bounds.depth * viewport.scale);
    const stepCount = 8;
    const stepGap = sD / stepCount;

    const treadLines: JSX.Element[] = [];
    for (let i = 1; i < stepCount; i++) {
      const yOffset = -sD / 2 + i * stepGap;
      treadLines.push(
        <Line
          key={`stair-tread-${item.id}-${i}`}
          points={[-sW / 2, yOffset, sW / 2, yOffset]}
          stroke="#555555"
          strokeWidth={1}
        />
      );
    }

    return (
      <Group key={`stair-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
        <Rect
          x={-sW / 2}
          y={-sD / 2}
          width={sW}
          height={sD}
          fill="#F5F5F5"
          stroke="#222222"
          strokeWidth={1.5}
        />
        {treadLines}
        <Line
          points={[0, sD / 2 - 4, 0, -sD / 2 + 8]}
          stroke="#333333"
          strokeWidth={1.5}
        />
        <Line
          points={[-4, -sD / 2 + 14, 0, -sD / 2 + 8, 4, -sD / 2 + 14]}
          stroke="#333333"
          strokeWidth={1.5}
        />
        <Text
          text="UP"
          x={-15}
          y={sD / 2 - 14}
          width={30}
          align="center"
          fontSize={9}
          fontStyle="bold"
          fill="#555555"
          fontFamily="Inter, sans-serif"
        />
      </Group>
    );
  }

  private renderChairPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(250, 250, 250, 0.9)",
        stroke: "#222222",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`chair-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#F5F5F5" stroke="#222222" strokeWidth={1.5} cornerRadius={3} />
        <Line points={[-sW / 2 + 2, -sD / 2 + 2, sW / 2 - 2, -sD / 2 + 2]} stroke="#555555" strokeWidth={1.5} />
      </Group>
    );
  }

  private renderTablePlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(250, 250, 250, 0.9)",
        stroke: "#1a1a1a",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`tbl-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#FAFAFA" stroke="#1a1a1a" strokeWidth={1.5} cornerRadius={2} />
      </Group>
    );
  }

  private renderDeskPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(250, 250, 250, 0.9)",
        stroke: "#1a1a1a",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`desk-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#FAFAFA" stroke="#1a1a1a" strokeWidth={1.5} cornerRadius={2} />
        <Line points={[-sW / 2, sD / 2 - 4, sW / 2, sD / 2 - 4]} stroke="#555555" strokeWidth={1} />
      </Group>
    );
  }

  private renderCabinetPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(245, 245, 245, 0.95)",
        stroke: "#2d2d2d",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`cab-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#F5F5F5" stroke="#2d2d2d" strokeWidth={1.5} cornerRadius={1} />
        <Line points={[-sW / 2 + 2, -sD / 2 + 2, sW / 2 - 2, -sD / 2 + 2]} stroke="#555555" strokeWidth={0.75} />
      </Group>
    );
  }

  private renderSofaPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(245, 245, 245, 0.9)",
        stroke: "#222222",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`sofa-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#F5F5F5" stroke="#222222" strokeWidth={1.5} cornerRadius={6} />
        <Rect x={-sW / 2 + 3} y={-sD / 2 + 2} width={sW - 6} height={sD * 0.3} fill="#E0E0E0" stroke="#333333" strokeWidth={1} cornerRadius={3} />
      </Group>
    );
  }

  private renderSanitaryPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    let bounds = { pos: item.position, width: item.widthMeters, depth: item.depthMeters, rotation: item.rotationDeg || 0 };
    if (item.geometry) {
      bounds = this.extractOrientedBounds(item.geometry);
    }
    const sPos = worldToScreen(bounds.pos, viewport);
    const sW = Math.max(14, bounds.width * viewport.scale);
    const sD = Math.max(14, bounds.depth * viewport.scale);

    return (
      <Group key={`san-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
        {/* Tank / cistern box */}
        <Rect
          x={-sW / 2}
          y={-sD / 2}
          width={sW}
          height={sD * 0.35}
          fill="#E8E8E8"
          stroke="#333333"
          strokeWidth={1.5}
          cornerRadius={2}
        />
        {/* Bowl — oval */}
        <Arc
          x={0}
          y={sD * 0.1}
          innerRadius={0}
          outerRadius={Math.min(sW, sD * 0.65) / 2}
          angle={360}
          rotation={0}
          fill="#F0F0F0"
          stroke="#333333"
          strokeWidth={1.5}
        />
      </Group>
    );
  }

  private renderEquipmentPlanSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(245, 245, 245, 0.9)",
        stroke: "#2d2d2d",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`eq-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#F5F5F5" stroke="#2d2d2d" strokeWidth={1.5} cornerRadius={1} />
      </Group>
    );
  }

  private renderGenericFurnitureSymbol(item: RenderFurniture, viewport: Viewport): JSX.Element {
    if (item.geometry) {
      return this.renderPolygonGeometry(item.id, item.geometry, viewport, {
        fill: "rgba(248, 248, 248, 0.9)",
        stroke: "#1a1a1a",
        strokeWidth: 1.5,
      });
    }
    const sPos = worldToScreen(item.position, viewport);
    const sW = item.widthMeters * viewport.scale;
    const sD = item.depthMeters * viewport.scale;
    return (
      <Group key={`gen-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg}>
        <Rect x={-sW / 2} y={-sD / 2} width={sW} height={sD} fill="#F8F8F8" stroke="#1a1a1a" strokeWidth={1.5} cornerRadius={2} />
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

      {/* Interactive Selection & Furniture Control Layer */}
      <Group key="layer-furniture-interactive">
        {model.furniture.map((item) => {
          const sPos = worldToScreen(item.position, viewport);
          const sW = item.widthMeters * viewport.scale;
          const sD = item.depthMeters * viewport.scale;
          const isSelected = selectedObjectId === item.id;
          const isEditable = !item.isLocked && !item.isImported;
          const isImportedItem = item.isImported || item.isLocked;

          // For imported structural or aperture elements (doors, windows, proxies):
          // Do NOT draw a default gray selection box or text label when unselected!
          if (isImportedItem && !isSelected) {
            return null;
          }

          return (
            <Group
              key={`furn-ctrl-${item.id}`}
              ref={(node) => {
                if (isSelected && isEditable) {
                  selectedNodeRef.current = node;
                }
              }}
              x={sPos.x}
              y={sPos.y}
              rotation={item.rotationDeg || 0}
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
              {/* Highlight selection box */}
              <Rect
                x={-sW / 2}
                y={-sD / 2}
                width={sW}
                height={sD}
                fill={
                  isSelected
                    ? "rgba(56, 189, 248, 0.25)"
                    : "rgba(180, 83, 9, 0.55)"
                }
                stroke={isSelected ? "#38bdf8" : "#f59e0b"}
                strokeWidth={isSelected ? 2 : 1.5}
                cornerRadius={2}
              />
              {(isSelected || !isImportedItem) && (
                <Text
                  text={item.name && !/^(door|window|space|polygon|multipolygon)$/i.test(item.name) ? item.name : item.itemType}
                  x={-sW / 2 + 2}
                  y={-sD / 2 + 2}
                  fontSize={Math.max(10, Math.min(12, sW / 4))}
                  fill={isSelected ? "#ffffff" : "#fef08a"}
                  fontFamily="Inter, sans-serif"
                  listening={false}
                />
              )}
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
