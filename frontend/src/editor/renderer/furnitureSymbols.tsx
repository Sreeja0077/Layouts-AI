/**
 * Architectural CAD 2D Furniture & Fixtures Symbol Renderer for Konva canvas adapter.
 * Renders professional, clean black-line Revit/AutoCAD style vector symbols.
 * 
 * CORE PRINCIPLES:
 * 1. ZERO INVENTED CHAIRS: A desk renders ONLY as a desk; a conference table renders ONLY as a table.
 *    Chairs are rendered ONLY when an actual IFC chair element exists in the model.
 * 2. EXACT 1-TO-1 FIDELITY: Each IFC entity produces exactly one symbol preserving source bounds and rotation.
 * 3. CLASSIC ARCHITECTURAL CAD STYLING: Clean linework (#222222 / #555555) on neutral fill (#FFFFFF / #FAFAFA).
 *    Zero rainbow/bright colorful fills.
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
 * Clean Office Desk Symbol (NO attached chairs).
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
  const sW = Math.max(16, bounds.width * viewport.scale);
  const sD = Math.max(10, bounds.depth * viewport.scale);

  return (
    <Group key={`desk-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Desk Surface Rect */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
        cornerRadius={1}
      />
      {/* Cable Grommet Indicator */}
      <Circle
        x={sW / 2 - Math.min(8, sW * 0.15)}
        y={-sD / 2 + Math.min(8, sD * 0.2)}
        radius={Math.max(1.5, Math.min(3, sW * 0.03))}
        fill="none"
        stroke="#555555"
        strokeWidth={0.8}
      />
      {/* Modesty / Drawer Line */}
      <Line
        points={[-sW / 2 + 3, sD / 2 - 3, sW / 2 - 3, sD / 2 - 3]}
        stroke="#666666"
        strokeWidth={0.8}
        dash={[2, 2]}
      />
    </Group>
  );
}

/**
 * Standalone Ergonomic Office / Swivel Chair CAD Symbol.
 * Rendered ONLY when an actual IFC chair element exists.
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
  const sW = Math.max(10, bounds.width * viewport.scale);
  const sD = Math.max(10, bounds.depth * viewport.scale);
  const radius = Math.min(sW, sD) / 2;

  return (
    <Group key={`chair-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* 5-Star Base Leg Lines */}
      <Line points={[0, 0, 0, -radius]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, -radius * 0.95, -radius * 0.31]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, radius * 0.95, -radius * 0.31]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, -radius * 0.59, radius * 0.81]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, radius * 0.59, radius * 0.81]} stroke="#555555" strokeWidth={0.8} />

      {/* Seat Cushion Circle */}
      <Circle
        x={0}
        y={0}
        radius={radius * 0.8}
        fill="#FAFAFA"
        stroke="#222222"
        strokeWidth={1.2}
      />
      {/* Backrest Curved Arc */}
      <Line
        points={[-radius * 0.75, -radius * 0.35, 0, -radius * 0.8, radius * 0.75, -radius * 0.35]}
        stroke="#222222"
        strokeWidth={1.5}
        tension={0.4}
      />
    </Group>
  );
}

/**
 * Conference Table Symbol (NO fake perimeter chairs).
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
  const sW = Math.max(30, bounds.width * viewport.scale);
  const sD = Math.max(16, bounds.depth * viewport.scale);

  return (
    <Group key={`conf-table-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Capsule / Oval Conference Table Surface */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.5}
        cornerRadius={Math.min(sD / 2, 12)}
      />

      {/* Central Cable Management & AV Inset Trough */}
      <Rect
        x={-sW / 4}
        y={-sD / 6}
        width={sW / 2}
        height={sD / 3}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
        cornerRadius={2}
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
  const sW = Math.max(14, bounds.width * viewport.scale);
  const sD = Math.max(14, bounds.depth * viewport.scale);

  return (
    <Group key={`table-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
        cornerRadius={2}
      />
    </Group>
  );
}

/**
 * Living Room / Reception Sofa & Sectional Couch.
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
  const sW = Math.max(24, bounds.width * viewport.scale);
  const sD = Math.max(14, bounds.depth * viewport.scale);
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
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
        cornerRadius={3}
      />

      {/* Backrest Cushion Line */}
      <Rect
        x={-sW / 2 + 2}
        y={-sD / 2 + 1}
        width={sW - 4}
        height={sD * 0.3}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
        cornerRadius={1}
      />

      {/* Seating Cushion Seam Dividers */}
      <Line
        points={[-sW / 6, -sD / 2 + sD * 0.3, -sW / 6, sD / 2 - 1]}
        stroke="#666666"
        strokeWidth={0.8}
      />
      <Line
        points={[sW / 6, -sD / 2 + sD * 0.3, sW / 6, sD / 2 - 1]}
        stroke="#666666"
        strokeWidth={0.8}
      />

      {/* Armrests */}
      <Rect
        x={-sW / 2 + 1}
        y={-sD / 2 + 1}
        width={Math.max(2, sW * 0.1)}
        height={sD - 2}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
      />
      <Rect
        x={sW / 2 - Math.max(2, sW * 0.1) - 1}
        y={-sD / 2 + 1}
        width={Math.max(2, sW * 0.1)}
        height={sD - 2}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
      />

      {/* L-Sectional Chaise Extension (if applicable) */}
      {isSectional && (
        <Rect
          x={sW / 2 - sW * 0.35}
          y={sD / 2}
          width={sW * 0.35}
          height={sD * 0.7}
          fill="#FFFFFF"
          stroke="#222222"
          strokeWidth={1.2}
          cornerRadius={2}
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
  const sW = Math.max(20, bounds.width * viewport.scale);
  const sD = Math.max(10, bounds.depth * viewport.scale);

  return (
    <Group key={`pantry-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      {/* Counter Top Surface */}
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
      />

      {/* Inset Sink Basin Cutout */}
      <Rect
        x={sW / 4 - 5}
        y={-sD / 3}
        width={10}
        height={sD * 0.66}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
        cornerRadius={2}
      />
      {/* Faucet Dot */}
      <Circle x={sW / 4} y={0} radius={1.5} fill="#333333" />
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
  const sW = Math.max(12, bounds.width * viewport.scale);
  const sD = Math.max(12, bounds.depth * viewport.scale);
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
          fill="#FFFFFF"
          stroke="#222222"
          strokeWidth={1.2}
          cornerRadius={1}
        />
        {/* Oval Toilet Bowl */}
        <Circle
          x={0}
          y={sD * 0.15}
          radius={sW * 0.45}
          fill="#FFFFFF"
          stroke="#222222"
          strokeWidth={1.2}
        />
        {/* Inner Bowl Rim */}
        <Circle
          x={0}
          y={sD * 0.15}
          radius={sW * 0.3}
          fill="none"
          stroke="#555555"
          strokeWidth={0.8}
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
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
        cornerRadius={2}
      />
      {/* Oval Sink Basin */}
      <Circle
        x={0}
        y={0}
        radius={Math.min(sW, sD) * 0.35}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
      />
      {/* Faucet Dot */}
      <Circle x={0} y={-sD * 0.3} radius={1.5} fill="#333333" />
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
  const sW = Math.max(14, bounds.width * viewport.scale);
  const sD = Math.max(8, bounds.depth * viewport.scale);

  return (
    <Group key={`cab-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
      />
      <Line
        points={[-sW / 2, -sD / 2, sW / 2, sD / 2]}
        stroke="#555555"
        strokeWidth={0.8}
        dash={[2, 2]}
      />
      <Line
        points={[-sW / 2, sD / 2, sW / 2, -sD / 2]}
        stroke="#555555"
        strokeWidth={0.8}
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
  const sW = Math.max(10, bounds.width * viewport.scale);
  const sD = Math.max(10, bounds.depth * viewport.scale);

  return (
    <Group key={`furn-gen-${item.id}`} x={sPos.x} y={sPos.y} rotation={bounds.rotation}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1}
        cornerRadius={1}
      />
    </Group>
  );
}
