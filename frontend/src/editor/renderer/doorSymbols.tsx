/**
 * Architectural CAD Standard Hinged Door Symbol Component for Konva canvas renderer.
 * Operates entirely in world metric coordinates and transforms resulting vertices
 * to screen space via worldToScreen(), guaranteeing zero coordinate-flip / inversion drift.
 */

import React from "react";
import { Group, Line } from "react-konva";
import { Viewport } from "../canvas/canvasTypes";
import { worldToScreen } from "../canvas/viewport";
import { calculateDoorOpeningOrientation } from "./roomOpeningUtils";
import { RenderPoint, RenderSpace, RenderWall } from "./renderTypes";

export function renderCadDoorSymbol(
  id: string,
  pos: RenderPoint,
  widthMeters: number,
  depthMeters: number,
  baseRotationDeg: number,
  viewport: Viewport,
  spaces: ReadonlyArray<RenderSpace> = [],
  walls: ReadonlyArray<RenderWall> = [],
  explicitHostWallId?: string,
  otherDoors: ReadonlyArray<{ pos?: RenderPoint; width?: number; id?: string }> = [],
  doorProperties?: Record<string, any>
): JSX.Element {
  const w = Math.max(0.6, widthMeters || 0.9);
  const d = Math.max(0.1, depthMeters || 0.15);

  const orientation = calculateDoorOpeningOrientation(
    pos,
    w,
    baseRotationDeg,
    spaces,
    walls,
    explicitHostWallId,
    otherDoors,
    doorProperties
  );

  const u = orientation.u;
  const n = orientation.interiorNormal;
  const vSwing: RenderPoint =
    orientation.swingDirection === "OUTWARD"
      ? { x: -n.x, y: -n.y }
      : n;

  // 1. Wall opening frame rectangle in world coordinates
  const c1: RenderPoint = {
    x: pos.x - (u.x * w) / 2 - (vSwing.x * d) / 2,
    y: pos.y - (u.y * w) / 2 - (vSwing.y * d) / 2,
  };
  const c2: RenderPoint = {
    x: pos.x + (u.x * w) / 2 - (vSwing.x * d) / 2,
    y: pos.y + (u.y * w) / 2 - (vSwing.y * d) / 2,
  };
  const c3: RenderPoint = {
    x: pos.x + (u.x * w) / 2 + (vSwing.x * d) / 2,
    y: pos.y + (u.y * w) / 2 + (vSwing.y * d) / 2,
  };
  const c4: RenderPoint = {
    x: pos.x - (u.x * w) / 2 + (vSwing.x * d) / 2,
    y: pos.y - (u.y * w) / 2 + (vSwing.y * d) / 2,
  };

  const sc1 = worldToScreen(c1, viewport);
  const sc2 = worldToScreen(c2, viewport);
  const sc3 = worldToScreen(c3, viewport);
  const sc4 = worldToScreen(c4, viewport);

  // 2. Wall jamb points & ticks in world coordinates
  const jStart: RenderPoint = {
    x: pos.x - (u.x * w) / 2,
    y: pos.y - (u.y * w) / 2,
  };
  const jEnd: RenderPoint = {
    x: pos.x + (u.x * w) / 2,
    y: pos.y + (u.y * w) / 2,
  };

  const tickExt = d / 2 + 0.05;
  const t1a = worldToScreen(
    { x: jStart.x - vSwing.x * tickExt, y: jStart.y - vSwing.y * tickExt },
    viewport
  );
  const t1b = worldToScreen(
    { x: jStart.x + vSwing.x * tickExt, y: jStart.y + vSwing.y * tickExt },
    viewport
  );
  const t2a = worldToScreen(
    { x: jEnd.x - vSwing.x * tickExt, y: jEnd.y - vSwing.y * tickExt },
    viewport
  );
  const t2b = worldToScreen(
    { x: jEnd.x + vSwing.x * tickExt, y: jEnd.y + vSwing.y * tickExt },
    viewport
  );

  // 3. Hinge & Strike Jamb assignment
  const hinge: RenderPoint = orientation.hingeSide === "END" ? jEnd : jStart;
  const leafAlongWall: RenderPoint =
    orientation.hingeSide === "END"
      ? { x: -u.x, y: -u.y }
      : u;

  // 4. Open leaf tip in world coordinates
  const leafOpen: RenderPoint = {
    x: hinge.x + vSwing.x * w,
    y: hinge.y + vSwing.y * w,
  };

  const sHinge = worldToScreen(hinge, viewport);
  const sLeafOpen = worldToScreen(leafOpen, viewport);

  // 5. 90-degree Circular Swing Arc in world coordinates
  const arcPointsScreen: number[] = [];
  const arcSegments = 24;
  for (let i = 0; i <= arcSegments; i++) {
    const angleRad = (i / arcSegments) * (Math.PI / 2);
    const arcWorldPt: RenderPoint = {
      x:
        hinge.x +
        leafAlongWall.x * (w * Math.cos(angleRad)) +
        vSwing.x * (w * Math.sin(angleRad)),
      y:
        hinge.y +
        leafAlongWall.y * (w * Math.cos(angleRad)) +
        vSwing.y * (w * Math.sin(angleRad)),
    };
    const sPt = worldToScreen(arcWorldPt, viewport);
    arcPointsScreen.push(sPt.x, sPt.y);
  }

  return (
    <Group key={`door-cad-${id}`}>
      {/* Wall opening cutout frame */}
      <Line
        points={[sc1.x, sc1.y, sc2.x, sc2.y, sc3.x, sc3.y, sc4.x, sc4.y]}
        closed
        fill="#FFFFFF"
        stroke="#111111"
        strokeWidth={1}
      />
      {/* Left Wall Jamb Tick */}
      <Line
        points={[t1a.x, t1a.y, t1b.x, t1b.y]}
        stroke="#111111"
        strokeWidth={1.5}
      />
      {/* Right Wall Jamb Tick */}
      <Line
        points={[t2a.x, t2a.y, t2b.x, t2b.y]}
        stroke="#111111"
        strokeWidth={1.5}
      />
      {/* 90-degree Door Swing Arc */}
      <Line
        points={arcPointsScreen}
        stroke="#555555"
        strokeWidth={1}
        dash={[3, 3]}
      />
      {/* Door Leaf Line attached to Hinge */}
      <Line
        points={[sHinge.x, sHinge.y, sLeafOpen.x, sLeafOpen.y]}
        stroke="#111111"
        strokeWidth={1.5}
        lineCap="round"
      />
    </Group>
  );
}
