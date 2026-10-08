/**
 * Persistent Collapsible Left Project & Model Navigator Sidebar for BIM Workstation.
 * Provides hierarchical tree views for Levels, Element Categories, Layout Variants, and Views.
 */

import React, { useState } from "react";
import {
  Building2,
  Layers,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  Box,
  DoorClosed,
  AppWindow,
  Columns,
  Grid,
  Sofa,
  ChevronLeft,
} from "lucide-react";
import { FloorPlanRenderModel } from "../../editor/renderer/renderTypes";

export interface ProjectNavigatorProps {
  renderModel?: FloorPlanRenderModel;
  availableStoreys?: string[];
  activeStorey?: string;
  onSelectStorey?: (storey: string) => void;
  availableFloorPlans?: Array<{ id: string; name: string }>;
  activeFloorPlanId?: string;
  onSelectFloorPlan?: (pId: string, fpId: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const ProjectNavigator: React.FC<ProjectNavigatorProps> = ({
  renderModel,
  availableStoreys = [],
  activeStorey,
  onSelectStorey,
  availableFloorPlans = [],
  activeFloorPlanId,
  onSelectFloorPlan,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    project: true,
    levels: true,
    elements: true,
  });

  const [categoryVisibility, setCategoryVisibility] = useState<Record<string, boolean>>({
    walls: true,
    doors: true,
    windows: true,
    columns: true,
    spaces: true,
    furniture: true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const toggleVisibility = (category: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCategoryVisibility((prev) => ({ ...prev, [category]: !prev[category] }));
  };

  if (isCollapsed) {
    return (
      <div
        style={{
          width: "40px",
          backgroundColor: "#FFFFFF",
          borderRight: "1px solid #D9DDE3",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: "12px",
          gap: "16px",
          boxSizing: "border-box",
        }}
      >
        <button
          onClick={onToggleCollapse}
          title="Expand Model Navigator"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#4B5563",
            padding: "6px",
            borderRadius: "4px",
          }}
        >
          <ChevronRight size={18} />
        </button>
        <div title="Project Levels"><Building2 size={18} color="#6B7280" /></div>
        <div title="Elements"><Layers size={18} color="#6B7280" /></div>
      </div>
    );
  }

  const wallsCount = renderModel?.walls?.length || 0;
  const doorsCount = renderModel?.doors?.length || 0;
  const windowsCount = renderModel?.windows?.length || 0;
  const columnsCount = renderModel?.columns?.length || 0;
  const spacesCount = renderModel?.spaces?.length || 0;
  const furnitureCount = renderModel?.furniture?.length || 0;

  return (
    <aside
      style={{
        width: "240px",
        backgroundColor: "#FFFFFF",
        borderRight: "1px solid #D9DDE3",
        display: "flex",
        flexDirection: "column",
        userSelect: "none",
        fontSize: "0.8rem",
        boxSizing: "border-box",
      }}
    >
      {/* Navigator Header */}
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
          <Building2 size={13} color="#2563EB" />
          <span>Model Navigator</span>
        </div>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            title="Collapse Navigator"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#9CA3AF",
              padding: "2px",
            }}
          >
            <ChevronLeft size={16} />
          </button>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {/* SECTION 1: FLOOR PLANS & DRAWINGS */}
        <div style={{ marginBottom: "8px" }}>
          <div
            onClick={() => toggleSection("project")}
            style={{
              padding: "6px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
              fontWeight: 700,
              color: "#4B5563",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            <span>FLOOR PLANS ({availableFloorPlans.length || 1})</span>
            {expandedSections.project ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.project && (
            <div style={{ paddingLeft: "8px" }}>
              {availableFloorPlans.length > 0 ? (
                availableFloorPlans.map((fp) => {
                  const isActive = fp.id === activeFloorPlanId;
                  return (
                    <div
                      key={fp.id}
                      onClick={() => onSelectFloorPlan && onSelectFloorPlan("proj_101", fp.id)}
                      style={{
                        padding: "5px 12px",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        cursor: "pointer",
                        backgroundColor: isActive ? "#EFF6FF" : "transparent",
                        color: isActive ? "#2563EB" : "#374151",
                        fontWeight: isActive ? 600 : 400,
                        borderLeft: isActive ? "3px solid #2563EB" : "3px solid transparent",
                      }}
                    >
                      <Layers size={13} color={isActive ? "#2563EB" : "#9CA3AF"} />
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {fp.name}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div
                  style={{
                    padding: "5px 12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    backgroundColor: "#EFF6FF",
                    color: "#2563EB",
                    fontWeight: 600,
                    borderLeft: "3px solid #2563EB",
                  }}
                >
                  <Layers size={13} color="#2563EB" />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {renderModel?.name || "Active Floor Plan"}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* SECTION 2: BUILDING LEVELS */}
        <div style={{ marginBottom: "8px" }}>
          <div
            onClick={() => toggleSection("levels")}
            style={{
              padding: "6px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
              fontWeight: 700,
              color: "#4B5563",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            <span>BUILDING STOREYS</span>
            {expandedSections.levels ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.levels && (
            <div style={{ paddingLeft: "8px" }}>
              {availableStoreys.length > 0 ? (
                availableStoreys.map((st) => {
                  const isActive = st === activeStorey;
                  return (
                    <div
                      key={st}
                      onClick={() => onSelectStorey && onSelectStorey(st)}
                      style={{
                        padding: "5px 12px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        cursor: "pointer",
                        backgroundColor: isActive ? "#EFF6FF" : "transparent",
                        color: isActive ? "#2563EB" : "#374151",
                        fontWeight: isActive ? 600 : 400,
                        borderLeft: isActive ? "3px solid #2563EB" : "3px solid transparent",
                      }}
                    >
                      <span>{st}</span>
                      <span style={{ fontSize: "0.65rem", color: "#9CA3AF" }}>BIM</span>
                    </div>
                  );
                })
              ) : (
                <div style={{ padding: "4px 12px", color: "#9CA3AF", fontStyle: "italic" }}>
                  Active Level Only
                </div>
              )}
            </div>
          )}
        </div>

        {/* SECTION 3: ARCHITECTURAL ELEMENTS */}
        <div>
          <div
            onClick={() => toggleSection("elements")}
            style={{
              padding: "6px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
              fontWeight: 700,
              color: "#4B5563",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            <span>MODEL ELEMENTS</span>
            {expandedSections.elements ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.elements && (
            <div style={{ paddingLeft: "8px" }}>
              <CategoryRow
                icon={<Box size={13} color="#475569" />}
                label="Walls"
                count={wallsCount}
                visible={categoryVisibility.walls}
                onToggle={(e) => toggleVisibility("walls", e)}
              />
              <CategoryRow
                icon={<DoorClosed size={13} color="#0284c7" />}
                label="Doors"
                count={doorsCount}
                visible={categoryVisibility.doors}
                onToggle={(e) => toggleVisibility("doors", e)}
              />
              <CategoryRow
                icon={<AppWindow size={13} color="#06b6d4" />}
                label="Windows"
                count={windowsCount}
                visible={categoryVisibility.windows}
                onToggle={(e) => toggleVisibility("windows", e)}
              />
              <CategoryRow
                icon={<Columns size={13} color="#d97706" />}
                label="Columns"
                count={columnsCount}
                visible={categoryVisibility.columns}
                onToggle={(e) => toggleVisibility("columns", e)}
              />
              <CategoryRow
                icon={<Grid size={13} color="#6366f1" />}
                label="Spaces"
                count={spacesCount}
                visible={categoryVisibility.spaces}
                onToggle={(e) => toggleVisibility("spaces", e)}
              />
              <CategoryRow
                icon={<Sofa size={13} color="#10b981" />}
                label="Furniture"
                count={furnitureCount}
                visible={categoryVisibility.furniture}
                onToggle={(e) => toggleVisibility("furniture", e)}
              />
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

interface CategoryRowProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  visible: boolean;
  onToggle: (e: React.MouseEvent) => void;
}

const CategoryRow: React.FC<CategoryRowProps> = ({ icon, label, count, visible, onToggle }) => {
  return (
    <div
      style={{
        padding: "4px 12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        color: "#374151",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {icon}
        <span>{label}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span
          style={{
            fontSize: "0.65rem",
            backgroundColor: "#F3F4F6",
            color: "#6B7280",
            padding: "1px 5px",
            borderRadius: "999px",
            fontWeight: 600,
          }}
        >
          {count}
        </span>
        <button
          onClick={onToggle}
          title={visible ? "Hide category" : "Show category"}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: visible ? "#6B7280" : "#D1D5DB",
            padding: "1px",
          }}
        >
          {visible ? <Eye size={12} /> : <EyeOff size={12} />}
        </button>
      </div>
    </div>
  );
};
