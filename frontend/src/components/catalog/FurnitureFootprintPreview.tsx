/**
 * 2D Metric Footprint Preview Component (Phase 7 Task 7.1).
 * Renders an accurate, dimensionally correct 2D CAD footprint of a catalog item.
 * Displays metric dimension lines, dimension labels (width x depth in meters),
 * and clearance boundary indicators.
 */

import React from "react";
import { CatalogFurnitureItem } from "../../api/catalog";

interface Props {
  item: CatalogFurnitureItem;
  size?: number; // Canvas display box size in pixels
}

export const FurnitureFootprintPreview: React.FC<Props> = ({ item, size = 160 }) => {
  const widthM = item.width_m || 1.0;
  const depthM = item.depth_m || 1.0;
  const clearance = item.clearance || { front_m: 0.8, back_m: 0.2, left_m: 0.2, right_m: 0.2 };

  // Total bounds including clearance
  const totalW = widthM + (clearance.left_m || 0.2) + (clearance.right_m || 0.2);
  const totalD = depthM + (clearance.front_m || 0.8) + (clearance.back_m || 0.2);

  // Compute scale to fit inside SVG viewbox with margin
  const maxDim = Math.max(totalW, totalD, 1.0);
  const paddingM = maxDim * 0.15;
  const viewDim = maxDim + paddingM * 2;

  // Center the item
  const centerX = viewDim / 2;
  const centerY = viewDim / 2;

  // Item rect coordinates in local metric space
  const itemLeft = centerX - widthM / 2;
  const itemTop = centerY - depthM / 2;

  // Clearance rect coordinates
  const clearLeft = itemLeft - (clearance.left_m || 0.2);
  const clearTop = itemTop - (clearance.back_m || 0.2);
  const clearW = widthM + (clearance.left_m || 0.2) + (clearance.right_m || 0.2);
  const clearD = depthM + (clearance.front_m || 0.8) + (clearance.back_m || 0.2);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        backgroundColor: "#0B132B",
        borderRadius: "8px",
        padding: "10px",
        border: "1px solid #1E293B",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${viewDim} ${viewDim}`}
        style={{ overflow: "visible" }}
      >
        {/* Drafting Grid Lines */}
        <defs>
          <pattern id={`cadGrid_${item.catalog_item_id}`} width={viewDim / 8} height={viewDim / 8} patternUnits="userSpaceOnUse">
            <path d={`M ${viewDim / 8} 0 L 0 0 0 ${viewDim / 8}`} fill="none" stroke="#1E293B" strokeWidth="0.02" />
          </pattern>
        </defs>
        <rect width={viewDim} height={viewDim} fill={`url(#cadGrid_${item.catalog_item_id})`} />

        {/* Clearance Buffer Outline (Dotted Purple/Blue) */}
        <rect
          x={clearLeft}
          y={clearTop}
          width={clearW}
          height={clearD}
          fill="rgba(56, 189, 248, 0.05)"
          stroke="#38BDF8"
          strokeWidth="0.03"
          strokeDasharray="0.08, 0.05"
          rx="0.04"
        />

        {/* Solid Furniture Footprint (Architectural Slate) */}
        <rect
          x={itemLeft}
          y={itemTop}
          width={widthM}
          height={depthM}
          fill="#1E293B"
          stroke="#0284C7"
          strokeWidth="0.05"
          rx="0.03"
        />

        {/* Front Direction Indicator (User Access Line) */}
        <line
          x1={itemLeft}
          y1={itemTop + depthM}
          x2={itemLeft + widthM}
          y2={itemTop + depthM}
          stroke="#38BDF8"
          strokeWidth="0.06"
        />

        {/* Width Dimension Line (Top) */}
        <line
          x1={itemLeft}
          y1={itemTop - 0.08}
          x2={itemLeft + widthM}
          y2={itemTop - 0.08}
          stroke="#94A3B8"
          strokeWidth="0.02"
        />
        {/* Width Dimension Ticks */}
        <line x1={itemLeft} y1={itemTop - 0.12} x2={itemLeft} y2={itemTop - 0.04} stroke="#94A3B8" strokeWidth="0.02" />
        <line x1={itemLeft + widthM} y1={itemTop - 0.12} x2={itemLeft + widthM} y2={itemTop - 0.04} stroke="#94A3B8" strokeWidth="0.02" />

        {/* Depth Dimension Line (Right) */}
        <line
          x1={itemLeft + widthM + 0.08}
          y1={itemTop}
          x2={itemLeft + widthM + 0.08}
          y2={itemTop + depthM}
          stroke="#94A3B8"
          strokeWidth="0.02"
        />
        {/* Depth Dimension Ticks */}
        <line x1={itemLeft + widthM + 0.04} y1={itemTop} x2={itemLeft + widthM + 0.12} y2={itemTop} stroke="#94A3B8" strokeWidth="0.02" />
        <line x1={itemLeft + widthM + 0.04} y1={itemTop + depthM} x2={itemLeft + widthM + 0.12} y2={itemTop + depthM} stroke="#94A3B8" strokeWidth="0.02" />
      </svg>

      {/* Verified Footprint Label */}
      <div style={{ marginTop: "6px", display: "flex", flexDirection: "column", alignItems: "center", gap: "2px" }}>
        <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38BDF8" }}>
          {widthM.toFixed(2)}m (W) × {depthM.toFixed(2)}m (D)
        </span>
        <span style={{ fontSize: "0.65rem", color: "#64748B", textTransform: "uppercase", letterSpacing: "0.04em" }}>
          Authoritative 2D CAD Footprint
        </span>
      </div>
    </div>
  );
};
