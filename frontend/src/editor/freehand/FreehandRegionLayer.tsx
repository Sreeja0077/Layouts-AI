/**
 * Konva Freehand Region Selection Render Layer Component (Task 6.1).
 * Renders the user's active/completed freehand stroke overlaid on the floor plan canvas.
 * Visually distinct from permanent architectural geometry (walls, doors, windows, furniture).
 */

import React, { useMemo } from "react";
import { Group, Line, Circle } from "react-konva";
import { FreehandStroke } from "./freehandTypes";

interface FreehandRegionLayerProps {
  stroke: FreehandStroke | null;
}

export const FreehandRegionLayer: React.FC<FreehandRegionLayerProps> = React.memo(({ stroke }) => {
  if (!stroke || stroke.points.length === 0) {
    return null;
  }

  // Flatten points for Konva Line component: [x1, y1, x2, y2, ...]
  const flatPoints = useMemo(() => {
    return stroke.points.flatMap((pt) => [pt.x, pt.y]);
  }, [stroke.points]);

  const startPt = stroke.points[0];

  return (
    <Group key="layer-freehand-region" listening={false}>
      {/* Freehand Stroke Line / Polygon */}
      {flatPoints.length >= 4 && (
        <Line
          points={flatPoints}
          closed={stroke.isClosed}
          stroke="#a855f7"
          strokeWidth={2.5}
          fill={stroke.isClosed ? "rgba(168, 85, 247, 0.18)" : undefined}
          lineCap="round"
          lineJoin="round"
          dash={stroke.isDrawing ? [6, 4] : undefined}
        />
      )}

      {/* Start Point Indicator Dot */}
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

      {/* Vertex markers when stroke is completed */}
      {stroke.isClosed &&
        stroke.points.map((pt, idx) => (
          <Circle
            key={`v-${idx}`}
            x={pt.x}
            y={pt.y}
            radius={2.5}
            fill="#e9d5ff"
            opacity={0.8}
          />
        ))}
    </Group>
  );
});

FreehandRegionLayer.displayName = "FreehandRegionLayer";
