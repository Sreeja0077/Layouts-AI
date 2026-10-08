/**
 * Architectural CAD Sectional / Overhead / Garage Door Symbol Component for Konva canvas renderer.
 * Visual representation per Image 4:
 * - Heavy wall jambs
 * - Multi-panel sectional door leaf bar along opening
 * - Overhead track guide lines extending into garage space
 * - NO 90-degree hinged swing arc
 */

import React from "react";
import { Circle, Group, Line, Rect } from "react-konva";
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
  const sW = Math.max(20, widthMeters * viewport.scale);
  const sD = Math.max(6, (depthMeters || 0.2) * viewport.scale);

  // Track length proportional to door width in world metric coordinates (width * 1.2)
  const trackLength = sW * 1.2;

  // Determine track direction based on interior normal orientation (+Y or -Y)
  const trackDirY = orientation.swingDirection === "OUTWARD" ? 1 : -1;
  const trackEndY = trackDirY * trackLength;

  // 4 equal sectional door panel divisions along opening width
  const panelCount = 4;
  const panelWidth = sW / panelCount;
  const panelLines: JSX.Element[] = [];

  for (let i = 1; i < panelCount; i++) {
    const xOffset = -sW / 2 + i * panelWidth;
    panelLines.push(
      <Line
        key={`garage-panel-${id}-${i}`}
        points={[xOffset, -sD / 2, xOffset, sD / 2]}
        stroke="#38bdf8"
        strokeWidth={1}
      />
    );
  }

  return (
    <Group key={`garage-cad-${id}`} x={sPos.x} y={sPos.y} rotation={rotationDeg}>
      {/* Wall opening cutout frame */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#0f172a"
        stroke="#0284c7"
        strokeWidth={1.5}
      />

      {/* Sectional Door Panels along Opening */}
      <Rect
        x={-sW / 2 + 2}
        y={-sD / 4}
        width={sW - 4}
        height={sD / 2}
        fill="rgba(56, 189, 248, 0.15)"
        stroke="#38bdf8"
        strokeWidth={1.5}
      />
      {panelLines}

      {/* Left Wall Jamb Bracket */}
      <Rect
        x={-sW / 2 - 3}
        y={-sD / 2 - 2}
        width={4}
        height={sD + 4}
        fill="#38bdf8"
        stroke="#0284c7"
        strokeWidth={1}
      />

      {/* Right Wall Jamb Bracket */}
      <Rect
        x={sW / 2 - 1}
        y={-sD / 2 - 2}
        width={4}
        height={sD + 4}
        fill="#38bdf8"
        stroke="#0284c7"
        strokeWidth={1}
      />

      {/* Left Overhead Track Guide Line extending into Garage Space */}
      <Line
        points={[-sW / 2 + 4, 0, -sW / 2 + 4, trackEndY]}
        stroke="#38bdf8"
        strokeWidth={1.5}
        dash={[6, 4]}
      />

      {/* Right Overhead Track Guide Line extending into Garage Space */}
      <Line
        points={[sW / 2 - 4, 0, sW / 2 - 4, trackEndY]}
        stroke="#38bdf8"
        strokeWidth={1.5}
        dash={[6, 4]}
      />

      {/* Roller Stops at track ends */}
      <Circle
        x={-sW / 2 + 4}
        y={trackEndY}
        radius={2.5}
        fill="#38bdf8"
      />
      <Circle
        x={sW / 2 - 4}
        y={trackEndY}
        radius={2.5}
        fill="#38bdf8"
      />
    </Group>
  );
}
