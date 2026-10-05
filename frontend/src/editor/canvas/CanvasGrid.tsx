/**
 * Architectural Drafting Grid Layer for Konva Canvas (Task 5.2).
 * Renders major (1.0m) and minor (0.25m) world-space grid lines bounded to container view.
 * Visual assistance only — zero domain or collision authority.
 */

import React, { useMemo } from "react";
import { Layer, Line } from "react-konva";
import { Viewport } from "./canvasTypes";

interface CanvasGridProps {
  viewport: Viewport;
  containerWidth: number;
  containerHeight: number;
  majorStepMeters?: number;
  minorStepMeters?: number;
}

export const CanvasGrid: React.FC<CanvasGridProps> = React.memo(({
  viewport,
  containerWidth,
  containerHeight,
  majorStepMeters = 1.0,
  minorStepMeters = 0.25,
}) => {
  const gridLines = useMemo(() => {
    if (viewport.scale <= 0 || containerWidth <= 0 || containerHeight <= 0) {
      return { minorLines: [], majorLines: [] };
    }

    // Determine visible world bounds
    const minWorldX = Math.floor((-viewport.x) / viewport.scale / minorStepMeters) * minorStepMeters;
    const maxWorldX = Math.ceil((containerWidth - viewport.x) / viewport.scale / minorStepMeters) * minorStepMeters;
    const minWorldY = Math.floor((-viewport.y) / viewport.scale / minorStepMeters) * minorStepMeters;
    const maxWorldY = Math.ceil((containerHeight - viewport.y) / viewport.scale / minorStepMeters) * minorStepMeters;

    const minorLines: number[][] = [];
    const majorLines: number[][] = [];

    // Vertical lines
    for (let x = minWorldX; x <= maxWorldX; x += minorStepMeters) {
      const screenX = x * viewport.scale + viewport.x;
      const points = [screenX, 0, screenX, containerHeight];
      const isMajor = Math.abs(x % majorStepMeters) < 0.001 || Math.abs(x % majorStepMeters - majorStepMeters) < 0.001;

      if (isMajor) {
        majorLines.push(points);
      } else if (viewport.scale >= 20) { // Only show minor grid when sufficiently zoomed in
        minorLines.push(points);
      }
    }

    // Horizontal lines
    for (let y = minWorldY; y <= maxWorldY; y += minorStepMeters) {
      const screenY = y * viewport.scale + viewport.y;
      const points = [0, screenY, containerWidth, screenY];
      const isMajor = Math.abs(y % majorStepMeters) < 0.001 || Math.abs(y % majorStepMeters - majorStepMeters) < 0.001;

      if (isMajor) {
        majorLines.push(points);
      } else if (viewport.scale >= 20) {
        minorLines.push(points);
      }
    }

    return { minorLines, majorLines };
  }, [viewport, containerWidth, containerHeight, majorStepMeters, minorStepMeters]);

  return (
    <Layer listening={false}>
      {/* Minor Grid Lines */}
      {gridLines.minorLines.map((pts, idx) => (
        <Line
          key={`minor-${idx}`}
          points={pts}
          stroke="#334155"
          strokeWidth={0.5}
          opacity={0.3}
          dash={[2, 2]}
        />
      ))}

      {/* Major Grid Lines */}
      {gridLines.majorLines.map((pts, idx) => (
        <Line
          key={`major-${idx}`}
          points={pts}
          stroke="#475569"
          strokeWidth={1}
          opacity={0.6}
        />
      ))}
    </Layer>
  );
});

CanvasGrid.displayName = "CanvasGrid";
