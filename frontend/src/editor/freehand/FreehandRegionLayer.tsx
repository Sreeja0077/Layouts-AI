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
  // If regionPreview with valid world points exists, render using worldToScreen projection
  const screenPoints = useMemo(() => {
    if (regionPreview && regionPreview.worldPoints.length > 0) {
      return regionPreview.worldPoints.map((worldPt) => worldToScreen(worldPt, viewport));
    }
    if (stroke && stroke.points.length > 0) {
      return stroke.points;
    }
    return [];
  }, [regionPreview, stroke, viewport]);

  if (screenPoints.length === 0) {
    return null;
  }

  // Flatten points for Konva Line component: [x1, y1, x2, y2, ...]
  const flatPoints = screenPoints.flatMap((pt) => [pt.x, pt.y]);
  const startPt = screenPoints[0];
  const isClosed = regionPreview?.isClosed ?? stroke?.isClosed ?? false;
  const isDrawing = stroke?.isDrawing ?? false;

  // Project centroid to screen space if available
  const screenCentroid = regionPreview?.centroid
    ? worldToScreen(regionPreview.centroid, viewport)
    : null;

  return (
    <Group key="layer-freehand-region" listening={false}>
      {/* Freehand Region Stroke Line / Closed Polygon */}
      {flatPoints.length >= 4 && (
        <Line
          points={flatPoints}
          closed={isClosed}
          stroke="#a855f7"
          strokeWidth={2.5}
          fill={isClosed ? "rgba(168, 85, 247, 0.18)" : undefined}
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
