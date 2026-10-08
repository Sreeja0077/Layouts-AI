/**
 * Architectural CAD 2D Furniture & Fixtures Symbol Renderer for Konva canvas adapter.
 * Renders Revit-quality plan view vector symbols for:
 * - Executive / Office Desks & Swivel Chairs
 * - Conference Tables & Perimeter Chairs
 * - Sofas, Couches & L-shaped Sectionals
 * - Pantry Counters, Dining Tables & Sinks
 * - Sanitary Fixtures (Toilets, Basin Sinks, Vanities)
 */

import React from "react";
import { Circle, Group, Line, Rect } from "react-konva";
import { Viewport } from "../canvas/canvasTypes";
import { worldToScreen } from "../canvas/viewport";
import { extractOrientedBounds } from "./geometryUtils";
import { RenderFurniture } from "./renderTypes";

/**
 * Dispatcher for all architectural furniture & fixture items in 2D floor plan canvas.
 */
export function renderFurnitureItem(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  const subtype = (item.subtype || item.itemType || "OTHER").toUpperCase();
  const sourceIfcType = (item.sourceIfcType || "").toUpperCase();
  const nameText = (item.name || "").toUpperCase();
  const combined = `${subtype} ${sourceIfcType} ${nameText}`;

  if (combined.includes("CONFERENCE") || subtype === "CONFERENCE_TABLE") {
    return renderConferenceTablePlanSymbol(item, viewport);
  }
  if (combined.includes("DESK") || subtype === "DESK" || combined.includes("WORKSTATION")) {
    return renderDeskPlanSymbol(item, viewport);
  }
  if (combined.includes("CHAIR") || subtype === "CHAIR" || combined.includes("SEAT")) {
    return renderChairPlanSymbol(item, viewport);
  }
  if (combined.includes("TABLE") || subtype === "TABLE" || combined.includes("DINING")) {
    return renderTablePlanSymbol(item, viewport);
  }
  if (combined.includes("SOFA") || subtype === "SOFA" || combined.includes("SECTIONAL") || combined.includes("COUCH")) {
    return renderSofaPlanSymbol(item, viewport);
  }
  if (combined.includes("PANTRY") || subtype === "PANTRY_COUNTER" || combined.includes("KITCHEN")) {
    return renderPantryCounterSymbol(item, viewport);
  }
  if (
    combined.includes("TOILET") ||
    subtype === "TOILET" ||
    combined.includes("BASIN") ||
    subtype === "BASIN" ||
    combined.includes("SINK") ||
    subtype === "SINK" ||
    subtype === "SANITARY" ||
    sourceIfcType === "IFCSANITARYTERMINAL"
  ) {
    return renderSanitaryPlanSymbol(item, viewport);
  }
  if (subtype === "CABINET" || subtype === "STORAGE") {
    return renderCabinetPlanSymbol(item, viewport);
  }

  return renderGenericFurnitureSymbol(item, viewport);
}

/**
 * Executive Office Desk with Grommet, Modesty Panel, and Ergonomic Swivel Chair.
 */
export function renderDeskPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 1.4,
    depth: item.depthMeters || 0.8,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(24, bounds.width * viewport.scale);
  const sD = Math.max(16, bounds.depth * viewport.scale);

  // Attached Ergonomic Swivel Chair dimensions (placed behind desk top)
  const chairRadius = Math.max(6, sD * 0.3);
  const chairOffsetY = sD / 2 + chairRadius + 4;

  return (
    <Group key={`desk-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Desk Surface Rect */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(30, 58, 138, 0.45)"
        stroke="#60a5fa"
        strokeWidth={1.5}
        cornerRadius={2}
      />
      {/* Cable Grommet Indicator */}
      <Circle
        x={sW / 2 - 8}
        y={-sD / 2 + 8}
        radius={3}
        fill="none"
        stroke="#93c5fd"
        strokeWidth={1}
      />
      {/* Modesty / Drawer Divider Line */}
      <Line
        points={[-sW / 2 + 4, sD / 2 - 4, sW / 2 - 4, sD / 2 - 4]}
        stroke="#93c5fd"
        strokeWidth={1}
        dash={[2, 2]}
      />

      {/* Ergonomic Swivel Chair behind Desk */}
      <Group y={chairOffsetY}>
        {/* Star base 5-point stem lines */}
        <Line points={[0, 0, 0, -chairRadius]} stroke="#94a3b8" strokeWidth={1} />
        <Line points={[0, 0, -chairRadius * 0.9, -chairRadius * 0.4]} stroke="#94a3b8" strokeWidth={1} />
        <Line points={[0, 0, chairRadius * 0.9, -chairRadius * 0.4]} stroke="#94a3b8" strokeWidth={1} />
        <Line points={[0, 0, -chairRadius * 0.6, chairRadius * 0.8]} stroke="#94a3b8" strokeWidth={1} />
        <Line points={[0, 0, chairRadius * 0.6, chairRadius * 0.8]} stroke="#94a3b8" strokeWidth={1} />

        {/* Seat Cushion Circle */}
        <Circle
          x={0}
          y={0}
          radius={chairRadius}
          fill="rgba(245, 158, 11, 0.65)"
          stroke="#fbbf24"
          strokeWidth={1.5}
        />
        {/* Curved Ergonomic Backrest */}
        <Line
          points={[-chairRadius, -chairRadius * 0.5, 0, -chairRadius * 0.9, chairRadius, -chairRadius * 0.5]}
          stroke="#fde047"
          strokeWidth={2}
          tension={0.5}
        />
        {/* Left Armrest */}
        <Rect
          x={-chairRadius - 3}
          y={-chairRadius * 0.4}
          width={3}
          height={chairRadius * 0.9}
          fill="#fbbf24"
          cornerRadius={1}
        />
        {/* Right Armrest */}
        <Rect
          x={chairRadius}
          y={-chairRadius * 0.4}
          width={3}
          height={chairRadius * 0.9}
          fill="#fbbf24"
          cornerRadius={1}
        />
      </Group>
    </Group>
  );
}

/**
 * Standalone Ergonomic Office / Swivel Chair CAD Symbol.
 */
export function renderChairPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 0.6,
    depth: item.depthMeters || 0.6,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(12, bounds.width * viewport.scale);
  const sD = Math.max(12, bounds.depth * viewport.scale);
  const radius = Math.min(sW, sD) / 2;

  return (
    <Group key={`chair-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* 5-Star Base Leg Lines */}
      <Line points={[0, 0, 0, -radius]} stroke="#94a3b8" strokeWidth={1} />
      <Line points={[0, 0, -radius * 0.95, -radius * 0.31]} stroke="#94a3b8" strokeWidth={1} />
      <Line points={[0, 0, radius * 0.95, -radius * 0.31]} stroke="#94a3b8" strokeWidth={1} />
      <Line points={[0, 0, -radius * 0.59, radius * 0.81]} stroke="#94a3b8" strokeWidth={1} />
      <Line points={[0, 0, radius * 0.59, radius * 0.81]} stroke="#94a3b8" strokeWidth={1} />

      {/* Seat Cushion Circle */}
      <Circle
        x={0}
        y={0}
        radius={radius * 0.85}
        fill="rgba(217, 119, 6, 0.75)"
        stroke="#fbbf24"
        strokeWidth={1.5}
      />
      {/* Backrest Line */}
      <Line
        points={[-radius * 0.8, -radius * 0.4, 0, -radius * 0.85, radius * 0.8, -radius * 0.4]}
        stroke="#fef08a"
        strokeWidth={2}
        tension={0.4}
      />
    </Group>
  );
}

/**
 * Conference Table with Automated Perimeter Chairs.
 */
export function renderConferenceTablePlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 3.0,
    depth: item.depthMeters || 1.4,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(40, bounds.width * viewport.scale);
  const sD = Math.max(24, bounds.depth * viewport.scale);

  // Calculate perimeter chairs around conference table
  const chairRadius = Math.max(5, sD * 0.18);
  const chairs: JSX.Element[] = [];

  // Top and bottom row chairs
  const numLongSide = Math.max(2, Math.floor(bounds.width / 0.8));
  for (let i = 0; i < numLongSide; i++) {
    const x = -sW / 2 + (sW / (numLongSide + 1)) * (i + 1);
    // Top chair
    chairs.push(
      <Circle
        key={`conf-chair-top-${i}`}
        x={x}
        y={-sD / 2 - chairRadius - 3}
        radius={chairRadius}
        fill="rgba(245, 158, 11, 0.7)"
        stroke="#fbbf24"
        strokeWidth={1}
      />
    );
    // Bottom chair
    chairs.push(
      <Circle
        key={`conf-chair-bot-${i}`}
        x={x}
        y={sD / 2 + chairRadius + 3}
        radius={chairRadius}
        fill="rgba(245, 158, 11, 0.7)"
        stroke="#fbbf24"
        strokeWidth={1}
      />
    );
  }

  // Left and right head chairs
  chairs.push(
    <Circle
      key="conf-chair-left"
      x={-sW / 2 - chairRadius - 3}
      y={0}
      radius={chairRadius}
      fill="rgba(245, 158, 11, 0.7)"
      stroke="#fbbf24"
      strokeWidth={1}
    />
  );
  chairs.push(
    <Circle
      key="conf-chair-right"
      x={sW / 2 + chairRadius + 3}
      y={0}
      radius={chairRadius}
      fill="rgba(245, 158, 11, 0.7)"
      stroke="#fbbf24"
      strokeWidth={1}
    />
  );

  return (
    <Group key={`conf-table-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Perimeter Chairs */}
      {chairs}

      {/* Capsule / Oval Conference Table Surface */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(99, 102, 241, 0.25)"
        stroke="#818cf8"
        strokeWidth={2}
        cornerRadius={sD / 2}
      />

      {/* Central Cable Management & AV Inset Trough */}
      <Rect
        x={-sW / 4}
        y={-sD / 6}
        width={sW / 2}
        height={sD / 3}
        fill="rgba(30, 27, 75, 0.5)"
        stroke="#a5b4fc"
        strokeWidth={1}
        cornerRadius={4}
      />
    </Group>
  );
}

/**
 * Standard Table (Dining / Work Table).
 */
export function renderTablePlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 1.2,
    depth: item.depthMeters || 0.8,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(16, bounds.width * viewport.scale);
  const sD = Math.max(16, bounds.depth * viewport.scale);

  return (
    <Group key={`table-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(16, 185, 129, 0.25)"
        stroke="#34d399"
        strokeWidth={1.5}
        cornerRadius={3}
      />
    </Group>
  );
}

/**
 * Living Room / Reception Sofa & L-shaped Sectional Couch.
 */
export function renderSofaPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 2.2,
    depth: item.depthMeters || 0.9,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(28, bounds.width * viewport.scale);
  const sD = Math.max(18, bounds.depth * viewport.scale);
  const isSectional =
    (item.subtype || "").toUpperCase().includes("SECTIONAL") ||
    (item.name || "").toUpperCase().includes("SECTIONAL");

  return (
    <Group key={`sofa-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Main Sofa Body */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(14, 116, 144, 0.35)"
        stroke="#22d3ee"
        strokeWidth={1.5}
        cornerRadius={4}
      />

      {/* Backrest Cushion Line */}
      <Rect
        x={-sW / 2 + 3}
        y={-sD / 2 + 2}
        width={sW - 6}
        height={sD * 0.35}
        fill="rgba(6, 182, 212, 0.5)"
        stroke="#67e8f9"
        strokeWidth={1}
        cornerRadius={2}
      />

      {/* Seating Cushion Seam Dividers */}
      <Line
        points={[-sW / 6, -sD / 2 + sD * 0.35, -sW / 6, sD / 2 - 2]}
        stroke="#a5f3fc"
        strokeWidth={1}
      />
      <Line
        points={[sW / 6, -sD / 2 + sD * 0.35, sW / 6, sD / 2 - 2]}
        stroke="#a5f3fc"
        strokeWidth={1}
      />

      {/* Armrests */}
      <Rect
        x={-sW / 2 + 2}
        y={-sD / 2 + 2}
        width={sW * 0.12}
        height={sD - 4}
        fill="#0891b2"
        cornerRadius={2}
      />
      <Rect
        x={sW / 2 - sW * 0.12 - 2}
        y={-sD / 2 + 2}
        width={sW * 0.12}
        height={sD - 4}
        fill="#0891b2"
        cornerRadius={2}
      />

      {/* L-Sectional Chaise Extension (if applicable) */}
      {isSectional && (
        <Rect
          x={sW / 2 - sW * 0.35}
          y={sD / 2}
          width={sW * 0.35}
          height={sD * 0.8}
          fill="rgba(14, 116, 144, 0.35)"
          stroke="#22d3ee"
          strokeWidth={1.5}
          cornerRadius={3}
        />
      )}
    </Group>
  );
}

/**
 * Pantry Counter & Kitchen Surface with Sink cutout.
 */
export function renderPantryCounterSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 1.8,
    depth: item.depthMeters || 0.6,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(24, bounds.width * viewport.scale);
  const sD = Math.max(12, bounds.depth * viewport.scale);

  return (
    <Group key={`pantry-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Counter Top Surface */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(236, 72, 153, 0.2)"
        stroke="#f472b6"
        strokeWidth={1.5}
      />

      {/* Inset Sink Basin Cutout */}
      <Rect
        x={sW / 4 - 6}
        y={-sD / 3}
        width={12}
        height={sD * 0.66}
        fill="rgba(15, 23, 42, 0.6)"
        stroke="#f472b6"
        strokeWidth={1}
        cornerRadius={3}
      />
      {/* Faucet Dot */}
      <Circle x={sW / 4} y={0} radius={2} fill="#f472b6" />
    </Group>
  );
}

/**
 * Sanitary Fixture CAD Symbols (Toilet, Vanity Sink, Basin).
 */
export function renderSanitaryPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 0.7,
    depth: item.depthMeters || 0.7,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(14, bounds.width * viewport.scale);
  const sD = Math.max(14, bounds.depth * viewport.scale);
  const isToilet =
    (item.subtype || "").toUpperCase().includes("TOILET") ||
    (item.name || "").toUpperCase().includes("TOILET") ||
    (item.name || "").toUpperCase().includes("WC");

  if (isToilet) {
    return (
      <Group key={`san-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
        {/* Toilet Water Tank Rect */}
        <Rect
          x={-sW / 2}
          y={-sD / 2}
          width={sW}
          height={sD * 0.35}
          fill="rgba(6, 182, 212, 0.4)"
          stroke="#22d3ee"
          strokeWidth={1.5}
          cornerRadius={2}
        />
        {/* Oval Toilet Bowl */}
        <Circle
          x={0}
          y={sD * 0.15}
          radius={sW * 0.45}
          fill="rgba(6, 182, 212, 0.3)"
          stroke="#67e8f9"
          strokeWidth={1.5}
        />
        {/* Inner Bowl Rim */}
        <Circle
          x={0}
          y={sD * 0.15}
          radius={sW * 0.3}
          fill="none"
          stroke="#a5f3fc"
          strokeWidth={1}
        />
      </Group>
    );
  }

  // Basin / Vanity Sink
  return (
    <Group key={`san-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Vanity Counter */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(6, 182, 212, 0.2)"
        stroke="#22d3ee"
        strokeWidth={1.5}
        cornerRadius={3}
      />
      {/* Oval Sink Basin */}
      <Circle
        x={0}
        y={0}
        radius={Math.min(sW, sD) * 0.35}
        fill="rgba(15, 23, 42, 0.6)"
        stroke="#67e8f9"
        strokeWidth={1}
      />
      {/* Faucet Dot */}
      <Circle x={0} y={-sD * 0.3} radius={2} fill="#67e8f9" />
    </Group>
  );
}

/**
 * Storage & Cabinet Symbol.
 */
export function renderCabinetPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 1.0,
    depth: item.depthMeters || 0.5,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(16, bounds.width * viewport.scale);
  const sD = Math.max(10, bounds.depth * viewport.scale);

  return (
    <Group key={`cab-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(107, 114, 128, 0.3)"
        stroke="#9ca3af"
        strokeWidth={1.5}
      />
      <Line
        points={[-sW / 2, -sD / 2, sW / 2, sD / 2]}
        stroke="#d1d5db"
        strokeWidth={1}
        dash={[2, 2]}
      />
      <Line
        points={[-sW / 2, sD / 2, sW / 2, -sD / 2]}
        stroke="#d1d5db"
        strokeWidth={1}
        dash={[2, 2]}
      />
    </Group>
  );
}

/**
 * Generic Fallback Furniture Symbol preserving actual bounds.
 */
export function renderGenericFurnitureSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  let bounds = {
    pos: item.position,
    width: item.widthMeters || 1.0,
    depth: item.depthMeters || 0.8,
    rotation: item.rotationDeg || 0,
  };
  if (item.geometry) {
    bounds = extractOrientedBounds(item.geometry);
  }

  const sPos = worldToScreen(bounds.pos, viewport);
  const sW = Math.max(12, bounds.width * viewport.scale);
  const sD = Math.max(12, bounds.depth * viewport.scale);

  return (
    <Group key={`furn-gen-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="rgba(148, 163, 184, 0.25)"
        stroke="#cbd5e1"
        strokeWidth={1}
        cornerRadius={2}
      />
    </Group>
  );
}
