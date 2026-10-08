/**
 * Architectural CAD Sectional / Overhead / Garage Door Symbol Component for Konva canvas renderer.
 * Operates in pure world metric coordinates and transforms vertices to screen space.
 * Features:
 * - Heavy wall jamb brackets
 * - Sectional door panel divisions along opening
 * - Overhead track guide lines extending into garage space
 * - NO 90-degree hinged swing arc
 */

import React from "react";
import { Circle, Group, Line } from "react-konva";
import { Viewport } from "../canvas/canvasTypes";
import { worldToScreen } from "../canvas/viewport";
import { calculateDoorOpeningOrientation } from "./roomOpeningUtils";
import { RenderPoint, RenderSpace, RenderWall } from "./renderTypes";

export function renderCadGarageDoorSymbol(
  id: string,
  pos: RenderPoint,
  widthMeters: number,
  depthMeters: number,
  baseRotationDeg: number,
  viewport: Viewport,
  spaces: ReadonlyArray<RenderSpace> = [],
  walls: ReadonlyArray<RenderWall> = [],
  explicitHostWallId?: string
): JSX.Element {
  const w = Math.max(1.8, widthMeters || 2.4);
  const d = Math.max(0.15, depthMeters || 0.2);

  const orientation = calculateDoorOpeningOrientation(
    pos,
    w,
    baseRotationDeg,
    spaces,
    walls,
    explicitHostWallId
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

  // 2. Sectional Door Panel Outline in world coordinates
  const pDepth = d * 0.5;
  const p1: RenderPoint = {
    x: pos.x - (u.x * (w - 0.1)) / 2 - (vSwing.x * pDepth) / 2,
    y: pos.y - (u.y * (w - 0.1)) / 2 - (vSwing.y * pDepth) / 2,
  };
  const p2: RenderPoint = {
    x: pos.x + (u.x * (w - 0.1)) / 2 - (vSwing.x * pDepth) / 2,
    y: pos.y + (u.y * (w - 0.1)) / 2 - (vSwing.y * pDepth) / 2,
  };
  const p3: RenderPoint = {
    x: pos.x + (u.x * (w - 0.1)) / 2 + (vSwing.x * pDepth) / 2,
    y: pos.y + (u.y * (w - 0.1)) / 2 + (vSwing.y * pDepth) / 2,
  };
  const p4: RenderPoint = {
    x: pos.x - (u.x * (w - 0.1)) / 2 + (vSwing.x * pDepth) / 2,
    y: pos.y - (u.y * (w - 0.1)) / 2 + (vSwing.y * pDepth) / 2,
  };

  const sp1 = worldToScreen(p1, viewport);
  const sp2 = worldToScreen(p2, viewport);
  const sp3 = worldToScreen(p3, viewport);
  const sp4 = worldToScreen(p4, viewport);

  // 3. Sectional 4 panel divisions
  const panelLines: JSX.Element[] = [];
  const panelCount = 4;
  for (let i = 1; i < panelCount; i++) {
    const frac = i / panelCount - 0.5;
    const ptA: RenderPoint = {
      x: pos.x + u.x * (w * frac) - (vSwing.x * pDepth) / 2,
      y: pos.y + u.y * (w * frac) - (vSwing.y * pDepth) / 2,
    };
    const ptB: RenderPoint = {
      x: pos.x + u.x * (w * frac) + (vSwing.x * pDepth) / 2,
      y: pos.y + u.y * (w * frac) + (vSwing.y * pDepth) / 2,
    };
    const sA = worldToScreen(ptA, viewport);
    const sB = worldToScreen(ptB, viewport);
    panelLines.push(
      <Line
        key={`garage-div-${id}-${i}`}
        points={[sA.x, sA.y, sB.x, sB.y]}
        stroke="#111111"
        strokeWidth={1}
      />
    );
  }

  // 4. Overhead track guide lines extending into garage space
  const trackLen = w * 1.0;
  const t1Start: RenderPoint = {
    x: pos.x - (u.x * w) / 2 + u.x * 0.1,
    y: pos.y - (u.y * w) / 2 + u.y * 0.1,
  };
  const t1End: RenderPoint = {
    x: t1Start.x + vSwing.x * trackLen,
    y: t1Start.y + vSwing.y * trackLen,
  };

  const t2Start: RenderPoint = {
    x: pos.x + (u.x * w) / 2 - u.x * 0.1,
    y: pos.y + (u.y * w) / 2 - u.y * 0.1,
  };
  const t2End: RenderPoint = {
    x: t2Start.x + vSwing.x * trackLen,
    y: t2Start.y + vSwing.y * trackLen,
  };

  const st1A = worldToScreen(t1Start, viewport);
  const st1B = worldToScreen(t1End, viewport);
  const st2A = worldToScreen(t2Start, viewport);
  const st2B = worldToScreen(t2End, viewport);

  return (
    <Group key={`garage-cad-${id}`}>
      {/* Wall opening cutout frame */}
      <Line
        points={[sc1.x, sc1.y, sc2.x, sc2.y, sc3.x, sc3.y, sc4.x, sc4.y]}
        closed
        fill="#FFFFFF"
        stroke="#111111"
        strokeWidth={1.2}
      />

      {/* Sectional Door Panels */}
      <Line
        points={[sp1.x, sp1.y, sp2.x, sp2.y, sp3.x, sp3.y, sp4.x, sp4.y]}
        closed
        fill="#FAFAFA"
        stroke="#111111"
        strokeWidth={1}
      />
      {panelLines}

      {/* Left Overhead Track Guide Line */}
      <Line
        points={[st1A.x, st1A.y, st1B.x, st1B.y]}
        stroke="#555555"
        strokeWidth={1}
        dash={[4, 4]}
      />

      {/* Right Overhead Track Guide Line */}
      <Line
        points={[st2A.x, st2A.y, st2B.x, st2B.y]}
        stroke="#555555"
        strokeWidth={1}
        dash={[4, 4]}
      />

      {/* Roller Stops at track ends */}
      <Circle x={st1B.x} y={st1B.y} radius={2.5} fill="#555555" />
      <Circle x={st2B.x} y={st2B.y} radius={2.5} fill="#555555" />
    </Group>
  );
}
