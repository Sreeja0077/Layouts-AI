/**
 * Bottom Status Bar for BIM 2D CAD Workstation.
 * Displays level elevation, drafting scale, world cursor coordinates, selected element, and metric units.
 */

import React from "react";
import { Point2D } from "../../editor/canvas/canvasTypes";

export interface StatusBarProps {
  activeStorey?: string;
  cursorWorldPt?: Point2D;
  scaleRatio?: number;
  totalElements?: number;
  selectedObjectId?: string | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  activeStorey = "Grade Level",
  cursorWorldPt = { x: 0, y: 0 },
  scaleRatio = 100,
  totalElements = 0,
  selectedObjectId,
}) => {
  return (
    <footer
      style={{
        height: "24px",
        backgroundColor: "#FFFFFF",
        borderTop: "1px solid #D9DDE3",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 12px",
        fontSize: "0.7rem",
        color: "#6B7280",
        userSelect: "none",
        zIndex: 10,
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div>
          <span style={{ color: "#9CA3AF" }}>Storey: </span>
          <span style={{ color: "#374151", fontWeight: 600 }}>{activeStorey}</span>
        </div>
        <div style={{ height: "12px", width: "1px", backgroundColor: "#E5E7EB" }} />
        <div>
          <span style={{ color: "#9CA3AF" }}>Scale: </span>
          <span style={{ color: "#374151", fontWeight: 600 }}>1:{Math.round(scaleRatio)}</span>
        </div>
        <div style={{ height: "12px", width: "1px", backgroundColor: "#E5E7EB" }} />
        <div>
          <span style={{ color: "#9CA3AF" }}>Cursor: </span>
          <span style={{ color: "#374151", fontWeight: 600 }}>
            X: {cursorWorldPt.x.toFixed(2)}m &nbsp; Y: {cursorWorldPt.y.toFixed(2)}m
          </span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div>
          <span style={{ color: "#9CA3AF" }}>Selection: </span>
          <span style={{ color: selectedObjectId ? "#2563EB" : "#374151", fontWeight: 600 }}>
            {selectedObjectId || "None"}
          </span>
        </div>
        <div style={{ height: "12px", width: "1px", backgroundColor: "#E5E7EB" }} />
        <div>
          <span style={{ color: "#9CA3AF" }}>Elements: </span>
          <span style={{ color: "#374151", fontWeight: 600 }}>{totalElements}</span>
        </div>
        <div style={{ height: "12px", width: "1px", backgroundColor: "#E5E7EB" }} />
        <div>
          <span style={{ color: "#9CA3AF" }}>Units: </span>
          <span style={{ color: "#374151", fontWeight: 600 }}>Metres (SI)</span>
        </div>
      </div>
    </footer>
  );
};
