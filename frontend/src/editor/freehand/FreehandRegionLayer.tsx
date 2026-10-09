/**
 * Konva Freehand Region Selection Render Layer Component (Task 6.1 & 6.2).
 * Renders the user's active/completed freehand stroke overlaid on the floor plan canvas.
 * Dynamically projects world-space region points (`worldPoints`) via active `viewport`
 * so the rendered overlay remains perfectly pinned to the floor plan during pan & zoom.
 */

import React, { useMemo } from "react";
import { Group, Line, Circle } from "react-konva";
import { Viewport } from "../canvas/canvasTypes";
import { worldToScreen } from "../canvas/viewport";
import { FreehandStroke, RegionPreview } from "./freehandTypes";

interface FreehandRegionLayerProps {
  stroke: FreehandStroke | null;
  regionPreview?: RegionPreview | null;
  viewport: Viewport;
}

export const FreehandRegionLayer: React.FC<FreehandRegionLayerProps> = React.memo(({
  stroke,
  regionPreview,
  viewport,
}) => {
  const serverVal = regionPreview?.serverValidation;
  const activeWorldPoints =
    serverVal && serverVal.isValid && serverVal.clippedWorldPoints.length > 0
      ? serverVal.clippedWorldPoints
      : regionPreview?.worldPoints;

  // If regionPreview with valid world points exists, render using worldToScreen projection
  const screenPoints = useMemo(() => {
    if (activeWorldPoints && activeWorldPoints.length > 0) {
      return activeWorldPoints.map((worldPt) => worldToScreen(worldPt, viewport));
    }
    if (stroke && stroke.points.length > 0) {
      return stroke.points;
    }
    return [];
  }, [activeWorldPoints, stroke, viewport]);

  if (screenPoints.length === 0) {
    return null;
  }

  // Flatten points for Konva Line component: [x1, y1, x2, y2, ...]
  const flatPoints = screenPoints.flatMap((pt) => [pt.x, pt.y]);
  const startPt = screenPoints[0];
  const isClosed = regionPreview?.isClosed ?? stroke?.isClosed ?? false;
  const isDrawing = stroke?.isDrawing ?? false;

  // Project centroid to screen space if available
  const activeCentroid = serverVal?.centroid || regionPreview?.centroid;
  const screenCentroid = activeCentroid
    ? worldToScreen(activeCentroid, viewport)
    : null;

  const strokeColor = serverVal?.isValid
    ? serverVal.isClipped
      ? "#0284c7"
      : "#16a34a"
    : "#a855f7";

  const fillColor = serverVal?.isValid
    ? serverVal.isClipped
      ? "rgba(56, 189, 248, 0.22)"
      : "rgba(34, 197, 94, 0.22)"
    : "rgba(168, 85, 247, 0.18)";

  return (
    <Group key="layer-freehand-region" listening={false}>
      {/* Freehand Region Stroke Line / Closed Polygon */}
      {flatPoints.length >= 4 && (
        <Line
          points={flatPoints}
          closed={isClosed}
          stroke={strokeColor}
          strokeWidth={2.5}
          fill={isClosed ? fillColor : undefined}
          lineCap="round"
          lineJoin="round"
          dash={isDrawing ? [6, 4] : undefined}
        />
      )}


      {/* Start Point Indicator Marker */}
      {startPt && (
        <Circle
          x={startPt.x}
          y={startPt.y}
          radius={5}
          fill="#c084fc"
          stroke="#ffffff"
          strokeWidth={1.5}
        />
      )}

      {/* Vertex Markers when region is closed */}
      {isClosed &&
        screenPoints.map((pt, idx) => (
          <Circle
            key={`v-${idx}`}
            x={pt.x}
            y={pt.y}
            radius={2.5}
            fill="#e9d5ff"
            opacity={0.8}
          />
        ))}

      {/* Centroid Marker Indicator */}
      {isClosed && screenCentroid && (
        <Circle
          x={screenCentroid.x}
          y={screenCentroid.y}
          radius={4}
          fill="#f43f5e"
          stroke="#ffffff"
          strokeWidth={1.5}
        />
      )}
    </Group>
  );
});

FreehandRegionLayer.displayName = "FreehandRegionLayer";
