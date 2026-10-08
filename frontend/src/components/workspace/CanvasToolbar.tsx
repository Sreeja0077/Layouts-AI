/**
 * Professional CAD Drafting Toolbar for Konva Canvas Editor.
 * Groups tools cleanly: SELECT, MODIFY, REGION DRAW, VIEW, and GRID TOGGLE.
 */

import React from "react";
import {
  MousePointer,
  Hand,
  Pencil,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Grid,
} from "lucide-react";
import { EditorToolMode } from "../../editor/freehand/freehandTypes";

export interface CanvasToolbarProps {
  toolMode: EditorToolMode;
  onSelectToolMode: (mode: EditorToolMode) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  showGrid: boolean;
  onToggleGrid: () => void;
}

export const CanvasToolbar: React.FC<CanvasToolbarProps> = ({
  toolMode,
  onSelectToolMode,
  onZoomIn,
  onZoomOut,
  onFitView,
  showGrid,
  onToggleGrid,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: "12px",
        left: "12px",
        backgroundColor: "#FFFFFF",
        border: "1px solid #D9DDE3",
        borderRadius: "6px",
        boxShadow: "0 2px 6px rgba(0, 0, 0, 0.08)",
        display: "flex",
        alignItems: "center",
        padding: "3px",
        gap: "2px",
        zIndex: 10,
        userSelect: "none",
      }}
    >
      {/* Tool Group 1: Select & Pan */}
      <ToolbarButton
        icon={<MousePointer size={14} />}
        label="Select (S)"
        isActive={toolMode === "select"}
        onClick={() => onSelectToolMode("select")}
      />
      <ToolbarButton
        icon={<Hand size={14} />}
        label="Pan Canvas (P)"
        isActive={toolMode === "pan"}
        onClick={() => onSelectToolMode("pan")}
      />
      <ToolbarButton
        icon={<Pencil size={14} />}
        label="Draw Freehand Region (R)"
        isActive={toolMode === "freehand_region"}
        onClick={() => onSelectToolMode("freehand_region")}
      />

      <div style={{ height: "16px", width: "1px", backgroundColor: "#E5E7EB", margin: "0 2px" }} />

      {/* Tool Group 2: View Controls */}
      <ToolbarButton icon={<ZoomIn size={14} />} label="Zoom In (+)" onClick={onZoomIn} />
      <ToolbarButton icon={<ZoomOut size={14} />} label="Zoom Out (-)" onClick={onZoomOut} />
      <ToolbarButton icon={<Maximize2 size={14} />} label="Fit View (F)" onClick={onFitView} />

      <div style={{ height: "16px", width: "1px", backgroundColor: "#E5E7EB", margin: "0 2px" }} />

      {/* Tool Group 3: Grid Toggle */}
      <ToolbarButton
        icon={<Grid size={14} />}
        label="Toggle Grid"
        isActive={showGrid}
        onClick={onToggleGrid}
      />
    </div>
  );
};

interface ToolbarButtonProps {
  icon: React.ReactNode;
  label: string;
  isActive?: boolean;
  onClick: () => void;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({ icon, label, isActive, onClick }) => {
  return (
    <button
      onClick={onClick}
      title={label}
      style={{
        backgroundColor: isActive ? "#EFF6FF" : "transparent",
        color: isActive ? "#2563EB" : "#4B5563",
        border: isActive ? "1px solid #BFDBFE" : "1px solid transparent",
        borderRadius: "4px",
        padding: "6px 8px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "all 0.1s ease",
      }}
    >
      {icon}
    </button>
  );
};
