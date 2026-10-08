/**
 * Architectural CAD Standard Hinged Door Symbol Component for Konva canvas renderer.
 * Operates in world metric coordinates transformed into screen pixels via Viewport.
 */

import React from "react";
import { Arc, Group, Line, Rect } from "react-konva";
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
  walls: ReadonlyArray<RenderWall> = []
): JSX.Element {
  const orientation = calculateDoorOpeningOrientation(
    pos,
    widthMeters,
    baseRotationDeg,
    spaces,
    walls
  );

  const rotationDeg = orientation.hostWallAngleDeg;
  const sPos = worldToScreen(pos, viewport);
  const sW = Math.max(12, widthMeters * viewport.scale);
  const sD = Math.max(4, depthMeters * viewport.scale);

  // Determine swing side flip (y-direction) based on interior normal orientation
  const isOutward = orientation.swingDirection === "OUTWARD";
  const flipFactor = isOutward ? -1 : 1;

  // Hinge point is at left wall jamb (-sW/2)
  const hingeX = -sW / 2;
  const leafEndY = -sW * flipFactor;
  const arcAngle = 90;
  const arcRotation = isOutward ? 0 : -90;

  return (
    <Group key={`door-cad-${id}`} x={sPos.x} y={sPos.y} rotation={rotationDeg}>
      {/* Wall opening cutout frame */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#0f172a"
        stroke="rgba(148, 163, 184, 0.4)"
        strokeWidth={1}
      />
      {/* Left Wall Jamb Tick */}
      <Line
        points={[-sW / 2, -sD / 2 - 2, -sW / 2, sD / 2 + 2]}
        stroke="#cbd5e1"
        strokeWidth={1.5}
      />
      {/* Right Wall Jamb Tick */}
      <Line
        points={[sW / 2, -sD / 2 - 2, sW / 2, sD / 2 + 2]}
        stroke="#cbd5e1"
        strokeWidth={1.5}
      />
      {/* 90-degree Interior Door Swing Arc */}
      <Arc
        x={hingeX}
        y={0}
        innerRadius={0}
        outerRadius={sW}
        angle={arcAngle}
        rotation={arcRotation}
        fill="rgba(56, 189, 248, 0.08)"
        stroke="#38bdf8"
        strokeWidth={1.5}
        dash={[4, 4]}
      />
      {/* Door Leaf Line attached to Hinge */}
      <Line
        points={[hingeX, 0, hingeX, leafEndY]}
        stroke="#60a5fa"
        strokeWidth={2.5}
        lineCap="round"
      />
    </Group>
  );
}
