/**
 * Architectural CAD 2D Furniture & Fixtures Symbol Renderer for Konva canvas adapter.
 * Renders professional, geometrically exact Revit/AutoCAD style vector symbols.
 * 
 * CORE PRINCIPLES:
 * 1. DIRECT VERTEX FOOTPRINT MAPPING: When an IFC element has polygon geometry (as verified
 *    in Technical Diagnostics), the exact polygon/multipolygon footprint vertices are rendered directly
 *    in screen space via worldToScreen(), preserving L-shapes, curves, angles, and custom profiles.
 * 2. LAYERED ARCHITECTURAL CAD DETAILS: Category-specific CAD details (backrests, grommets, basins,
 *    cushion seams) are rendered within the exact polygon footprint.
 * 3. ZERO INVENTED CHAIRS: A desk renders ONLY as a desk; a conference table renders ONLY as a table.
 *    Chairs are rendered ONLY when an actual IFC chair element exists in the model.
 * 4. EXACT 1-TO-1 FIDELITY: Each IFC entity produces exactly one symbol preserving source bounds and rotation.
 */

import React from "react";
import { Circle, Group, Line, Rect } from "react-konva";
import { Viewport } from "../canvas/canvasTypes";
import { worldToScreen } from "../canvas/viewport";
import { extractOrientedBounds } from "./geometryUtils";
import { RenderFurniture, RenderGeometry } from "./renderTypes";

/**
 * Checks if an item has valid polygon geometry extracted from the IFC model.
 */
function hasValidPolygonGeometry(geometry?: RenderGeometry): boolean {
  if (!geometry || !geometry.polygons || geometry.polygons.length === 0) {
    return false;
  }
  const firstPoly = geometry.polygons[0];
  return Boolean(firstPoly && firstPoly.exterior && firstPoly.exterior.length >= 3);
}

/**
 * Renders exact polygon/multipolygon footprint directly from IFC geometry vertices.
 */
function renderExactPolygonFootprint(
  id: string,
  geometry: RenderGeometry,
  viewport: Viewport,
  options: {
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    dash?: number[];
  } = {}
): JSX.Element {
  const fill = options.fill || "#FFFFFF";
  const stroke = options.stroke || "#222222";
  const strokeWidth = options.strokeWidth ?? 1.2;

  return (
    <React.Fragment key={`geom-footprint-${id}`}>
      {geometry.polygons.map((poly, polyIdx) => {
        const extPts = poly.exterior.flatMap((pt) => {
          const s = worldToScreen(pt, viewport);
          return [s.x, s.y];
        });
        if (extPts.length < 6) return null;

        return (
          <React.Fragment key={`poly-${id}-${polyIdx}`}>
            {/* Outer exterior boundary */}
            <Line
              points={extPts}
              closed
              fill={fill}
              stroke={stroke}
              strokeWidth={strokeWidth}
              dash={options.dash}
            />
            {/* Interior holes */}
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
                  fill="#FFFFFF"
                  stroke={stroke}
                  strokeWidth={1}
                />
              );
            })}
          </React.Fragment>
        );
      })}
    </React.Fragment>
  );
}

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
 * Clean Office Desk / Workstation Symbol (NO attached chairs).
 * If exact IFC geometry is present, projects vertices directly.
 */
export function renderDeskPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  if (hasValidPolygonGeometry(item.geometry)) {
    const bounds = extractOrientedBounds(item.geometry!);
    const sPos = worldToScreen(bounds.pos, viewport);

    return (
      <Group key={`desk-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
        {/* Subtle cable grommet near center */}
        <Circle
          x={sPos.x}
          y={sPos.y}
          radius={Math.max(1.5, Math.min(3, bounds.width * viewport.scale * 0.03))}
          fill="none"
          stroke="#555555"
          strokeWidth={0.8}
        />
      </Group>
    );
  }

  // Fallback parametric rectangular desk
  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(16, item.widthMeters * viewport.scale);
  const sD = Math.max(10, item.depthMeters * viewport.scale);

  return (
    <Group key={`desk-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
      <Circle
        x={sW / 2 - Math.min(8, sW * 0.15)}
        y={-sD / 2 + Math.min(8, sD * 0.2)}
        radius={Math.max(1.5, Math.min(3, sW * 0.03))}
        fill="none"
        stroke="#555555"
        strokeWidth={0.8}
      />
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
  if (hasValidPolygonGeometry(item.geometry)) {
    const bounds = extractOrientedBounds(item.geometry!);
    const sPos = worldToScreen(bounds.pos, viewport);
    const radius = Math.min(bounds.width, bounds.depth) * viewport.scale * 0.35;

    return (
      <Group key={`chair-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FAFAFA",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
        {/* Inner seat indicator */}
        <Circle
          x={sPos.x}
          y={sPos.y}
          radius={Math.max(2, radius)}
          fill="#FFFFFF"
          stroke="#555555"
          strokeWidth={0.8}
        />
      </Group>
    );
  }

  // Fallback parametric chair
  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(10, item.widthMeters * viewport.scale);
  const sD = Math.max(10, item.depthMeters * viewport.scale);
  const radius = Math.min(sW, sD) / 2;

  return (
    <Group key={`chair-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
      <Line points={[0, 0, 0, -radius]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, -radius * 0.95, -radius * 0.31]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, radius * 0.95, -radius * 0.31]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, -radius * 0.59, radius * 0.81]} stroke="#555555" strokeWidth={0.8} />
      <Line points={[0, 0, radius * 0.59, radius * 0.81]} stroke="#555555" strokeWidth={0.8} />
      <Circle
        x={0}
        y={0}
        radius={radius * 0.8}
        fill="#FAFAFA"
        stroke="#222222"
        strokeWidth={1.2}
      />
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
 * Directly projects exact multi-vertex boardroom / conference polygon footprints.
 */
export function renderConferenceTablePlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  if (hasValidPolygonGeometry(item.geometry)) {
    const bounds = extractOrientedBounds(item.geometry!);
    const sPos = worldToScreen(bounds.pos, viewport);
    const sW = bounds.width * viewport.scale;
    const sD = bounds.depth * viewport.scale;

    return (
      <Group key={`conf-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.5,
        })}
        {/* Central AV / cable management trough */}
        <Rect
          x={sPos.x - (sW * 0.25) / 2}
          y={sPos.y - (sD * 0.25) / 2}
          width={Math.max(10, sW * 0.25)}
          height={Math.max(4, sD * 0.25)}
          fill="#FAFAFA"
          stroke="#555555"
          strokeWidth={0.8}
          cornerRadius={2}
        />
      </Group>
    );
  }

  // Fallback parametric conference table
  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(30, item.widthMeters * viewport.scale);
  const sD = Math.max(16, item.depthMeters * viewport.scale);

  return (
    <Group key={`conf-table-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
  if (hasValidPolygonGeometry(item.geometry)) {
    return (
      <Group key={`table-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
      </Group>
    );
  }

  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(14, item.widthMeters * viewport.scale);
  const sD = Math.max(14, item.depthMeters * viewport.scale);

  return (
    <Group key={`table-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
 * Living Room / Reception Sofa, Couch & Sectional (L-shaped, U-shaped, Linear).
 * Renders exact L-shaped and custom polygon footprints directly from IFC vertices.
 */
export function renderSofaPlanSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  if (hasValidPolygonGeometry(item.geometry)) {
    return (
      <Group key={`sofa-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.4,
        })}
      </Group>
    );
  }

  // Fallback parametric linear / sectional sofa
  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(24, item.widthMeters * viewport.scale);
  const sD = Math.max(14, item.depthMeters * viewport.scale);
  const isSectional =
    (item.subtype || "").toUpperCase().includes("SECTIONAL") ||
    (item.name || "").toUpperCase().includes("SECTIONAL");

  return (
    <Group key={`sofa-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
  if (hasValidPolygonGeometry(item.geometry)) {
    return (
      <Group key={`pantry-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
      </Group>
    );
  }

  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(20, item.widthMeters * viewport.scale);
  const sD = Math.max(10, item.depthMeters * viewport.scale);

  return (
    <Group key={`pantry-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
      <Rect
        x={-sW / 2}
        y={-sD / 2}
        width={sW}
        height={sD}
        fill="#FFFFFF"
        stroke="#222222"
        strokeWidth={1.2}
      />
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
  if (hasValidPolygonGeometry(item.geometry)) {
    const bounds = extractOrientedBounds(item.geometry!);
    const sPos = worldToScreen(bounds.pos, viewport);
    const radius = Math.min(bounds.width, bounds.depth) * viewport.scale * 0.25;

    return (
      <Group key={`san-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
        <Circle
          x={sPos.x}
          y={sPos.y}
          radius={Math.max(2, radius)}
          fill="#FAFAFA"
          stroke="#555555"
          strokeWidth={0.8}
        />
      </Group>
    );
  }

  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(12, item.widthMeters * viewport.scale);
  const sD = Math.max(12, item.depthMeters * viewport.scale);
  const isToilet =
    (item.subtype || "").toUpperCase().includes("TOILET") ||
    (item.name || "").toUpperCase().includes("TOILET") ||
    (item.name || "").toUpperCase().includes("WC");

  if (isToilet) {
    return (
      <Group key={`san-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
        <Circle
          x={0}
          y={sD * 0.15}
          radius={sW * 0.45}
          fill="#FFFFFF"
          stroke="#222222"
          strokeWidth={1.2}
        />
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

  return (
    <Group key={`san-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
      <Circle
        x={0}
        y={0}
        radius={Math.min(sW, sD) * 0.35}
        fill="#FAFAFA"
        stroke="#555555"
        strokeWidth={0.8}
      />
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
  if (hasValidPolygonGeometry(item.geometry)) {
    return (
      <Group key={`cab-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
      </Group>
    );
  }

  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(14, item.widthMeters * viewport.scale);
  const sD = Math.max(8, item.depthMeters * viewport.scale);

  return (
    <Group key={`cab-sym-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
 * Generic Fallback Furniture Symbol preserving actual exact footprint.
 */
export function renderGenericFurnitureSymbol(
  item: RenderFurniture,
  viewport: Viewport
): JSX.Element {
  if (hasValidPolygonGeometry(item.geometry)) {
    return (
      <Group key={`gen-geom-${item.id}`}>
        {renderExactPolygonFootprint(item.id, item.geometry!, viewport, {
          fill: "#FFFFFF",
          stroke: "#222222",
          strokeWidth: 1.2,
        })}
      </Group>
    );
  }

  const sPos = worldToScreen(item.position, viewport);
  const sW = Math.max(10, item.widthMeters * viewport.scale);
  const sD = Math.max(10, item.depthMeters * viewport.scale);

  return (
    <Group key={`furn-gen-${item.id}`} x={sPos.x} y={sPos.y} rotation={item.rotationDeg || 0}>
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
