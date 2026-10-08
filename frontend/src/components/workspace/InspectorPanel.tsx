/**
 * Right BIM Properties Inspector Panel for Layouts AI 2D Editor.
 * Displays contextual architectural metadata for selected element or floor plan overview.
 */

import React, { useState } from "react";
import {
  Info,
  Layers,
  ChevronDown,
  ChevronRight,
  SlidersHorizontal,
  Lock,
  Unlock,
} from "lucide-react";
import {
  FloorPlanRenderModel,
  RenderDoor,
  RenderFurniture,
  RenderSpace,
  RenderWall,
} from "../../editor/renderer/renderTypes";

export interface InspectorPanelProps {
  renderModel?: FloorPlanRenderModel;
  selectedObjectId?: string | null;
  onClearSelection?: () => void;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  renderModel,
  selectedObjectId,
  onClearSelection,
}) => {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    general: true,
    dimensions: true,
    ifc: false,
  });

  const toggleGroup = (group: string) => {
    setExpandedGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  };

  // Find selected element from renderModel
  let selectedElement: any = null;
  let elementType: "WALL" | "DOOR" | "WINDOW" | "SPACE" | "FURNITURE" | null = null;

  if (selectedObjectId && renderModel) {
    const wall = renderModel.walls?.find((w) => w.id === selectedObjectId);
    if (wall) {
      selectedElement = wall;
      elementType = "WALL";
    }
    const door = renderModel.doors?.find((d) => d.id === selectedObjectId);
    if (door) {
      selectedElement = door;
      elementType = "DOOR";
    }
    const space = renderModel.spaces?.find((s) => s.id === selectedObjectId);
    if (space) {
      selectedElement = space;
      elementType = "SPACE";
    }
    const furn = renderModel.furniture?.find((f) => f.id === selectedObjectId);
    if (furn) {
      selectedElement = furn;
      elementType = "FURNITURE";
    }
  }

  return (
    <aside
      style={{
        width: "300px",
        backgroundColor: "#FFFFFF",
        borderLeft: "1px solid #D9DDE3",
        display: "flex",
        flexDirection: "column",
        fontSize: "0.8rem",
        userSelect: "none",
        boxSizing: "border-box",
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          height: "36px",
          padding: "0 12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #E5E7EB",
          backgroundColor: "#F9FAFB",
          fontWeight: 700,
          color: "#374151",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          fontSize: "0.7rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <SlidersHorizontal size={13} color="#2563EB" />
          <span>Properties Inspector</span>
        </div>
        {selectedObjectId && (
          <button
            onClick={onClearSelection}
            style={{
              background: "none",
              border: "none",
              color: "#2563EB",
              fontSize: "0.7rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Clear Selection
          </button>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px" }}>
        {selectedElement ? (
          <div>
            {/* ELEMENT TYPE BADGE */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "12px",
                paddingBottom: "8px",
                borderBottom: "1px solid #F3F4F6",
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    backgroundColor: "#EFF6FF",
                    color: "#2563EB",
                    padding: "2px 6px",
                    borderRadius: "4px",
                  }}
                >
                  {elementType}
                </span>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#1F2937", marginTop: "4px" }}>
                  {selectedElement.name || selectedElement.subtype || selectedElement.id}
                </div>
              </div>
              {selectedElement.isLocked && <span title="Object is locked"><Lock size={14} color="#D97706" /></span>}
            </div>

            {/* GROUP 1: GENERAL PROPERTIES */}
            <PropertyGroup
              title="GENERAL"
              isOpen={expandedGroups.general}
              onToggle={() => toggleGroup("general")}
            >
              <PropertyRow label="Element ID" value={selectedElement.id} />
              {selectedElement.subtype && <PropertyRow label="Subtype" value={selectedElement.subtype} />}
              {selectedElement.sourceIfcType && <PropertyRow label="IFC Class" value={selectedElement.sourceIfcType} />}
              {selectedElement.storeyName && <PropertyRow label="Storey Level" value={selectedElement.storeyName} />}
            </PropertyGroup>

            {/* GROUP 2: SPATIAL DIMENSIONS */}
            <PropertyGroup
              title="DIMENSIONS & POSITION"
              isOpen={expandedGroups.dimensions}
              onToggle={() => toggleGroup("dimensions")}
            >
              {selectedElement.position && (
                <PropertyRow
                  label="Position (X, Y)"
                  value={`${selectedElement.position.x.toFixed(2)}m, ${selectedElement.position.y.toFixed(2)}m`}
                />
              )}
              {selectedElement.widthMeters !== undefined && (
                <PropertyRow label="Width" value={`${selectedElement.widthMeters.toFixed(2)} m`} />
              )}
              {selectedElement.depthMeters !== undefined && (
                <PropertyRow label="Depth" value={`${selectedElement.depthMeters.toFixed(2)} m`} />
              )}
              {selectedElement.rotationDeg !== undefined && (
                <PropertyRow label="Rotation" value={`${selectedElement.rotationDeg.toFixed(1)}°`} />
              )}
            </PropertyGroup>

            {/* GROUP 3: IFC PROPERTIES */}
            {selectedElement.properties && Object.keys(selectedElement.properties).length > 0 && (
              <PropertyGroup
                title="IFC BIM ATTRIBUTES"
                isOpen={expandedGroups.ifc}
                onToggle={() => toggleGroup("ifc")}
              >
                {Object.entries(selectedElement.properties).slice(0, 10).map(([k, v]) => (
                  <PropertyRow key={k} label={k} value={String(v)} />
                ))}
              </PropertyGroup>
            )}
          </div>
        ) : (
          /* NO SELECTION: SHOW FLOOR PLAN OVERVIEW */
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <Layers size={16} color="#2563EB" />
              <div>
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#1F2937" }}>
                  {renderModel?.name || "Floor Plan Summary"}
                </div>
                <div style={{ fontSize: "0.7rem", color: "#6B7280" }}>
                  {renderModel?.activeStorey || "All Active Storeys"}
                </div>
              </div>
            </div>

            <PropertyGroup title="ELEMENT COUNTS" isOpen={true} onToggle={() => {}}>
              <PropertyRow label="Total Walls" value={String(renderModel?.walls?.length || 0)} />
              <PropertyRow label="Total Doors" value={String(renderModel?.doors?.length || 0)} />
              <PropertyRow label="Total Windows" value={String(renderModel?.windows?.length || 0)} />
              <PropertyRow label="Total Columns" value={String(renderModel?.columns?.length || 0)} />
              <PropertyRow label="Total Spaces/Rooms" value={String(renderModel?.spaces?.length || 0)} />
              <PropertyRow label="Total Furniture Items" value={String(renderModel?.furniture?.length || 0)} />
            </PropertyGroup>

            <div
              style={{
                marginTop: "16px",
                padding: "10px",
                backgroundColor: "#F9FAFB",
                borderRadius: "6px",
                border: "1px solid #E5E7EB",
                fontSize: "0.75rem",
                color: "#6B7280",
                display: "flex",
                gap: "6px",
              }}
            >
              <Info size={14} color="#2563EB" style={{ flexShrink: 0, marginTop: "2px" }} />
              <span>Select any element in the 2D drafting canvas to inspect and modify BIM properties.</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

interface PropertyGroupProps {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const PropertyGroup: React.FC<PropertyGroupProps> = ({ title, isOpen, onToggle, children }) => {
  return (
    <div style={{ marginBottom: "12px" }}>
      <div
        onClick={onToggle}
        style={{
          padding: "4px 0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          fontWeight: 700,
          color: "#4B5563",
          fontSize: "0.68rem",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          borderBottom: "1px solid #F3F4F6",
          marginBottom: "6px",
        }}
      >
        <span>{title}</span>
        {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </div>
      {isOpen && <div>{children}</div>}
    </div>
  );
};

const PropertyRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "3px 0",
      fontSize: "0.75rem",
    }}
  >
    <span style={{ color: "#6B7280" }}>{label}</span>
    <span
      style={{
        color: "#1F2937",
        fontWeight: 600,
        maxWidth: "160px",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}
    >
      {value}
    </span>
  </div>
);
