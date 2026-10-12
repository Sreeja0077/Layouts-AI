/**
 * Top Navigation Bar for Enterprise BIM Architectural Workstation.
 * Displays project branding, unified breadcrumbs (Project / Layout / Level),
 * view modes, AI layout trigger, and verification/autosave status.
 */

import React from "react";
import {
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  FolderOpen,
} from "lucide-react";

export interface TopNavProps {
  projectName?: string;
  floorPlanName?: string;
  projects?: Array<{ id: string; name: string }>;
  onSwitchProject?: (pId: string) => void;
  availableFloorPlans?: Array<{ id: string; name: string }>;
  activeFloorPlanId?: string;
  onSwitchFloorPlan?: (pId: string, fpId: string) => void;
  activeProjectId?: string;
  availableStoreys?: string[];
  activeStorey?: string;
  onSwitchStorey?: (storey: string) => void;
  activeTab: "workspace" | "editor" | "diagnostics";
  onTabChange: (tab: "workspace" | "editor" | "diagnostics") => void;
  isVerified?: boolean;
  onOpenUpload: () => void;
  onTriggerAI?: () => void;
  isAiActive?: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({
  projectName,
  floorPlanName = "Floor Plan 01",
  projects = [],
  availableFloorPlans = [],
  activeFloorPlanId,
  onSwitchFloorPlan,
  activeProjectId = "proj_101",
  availableStoreys = [],
  activeStorey,
  onSwitchStorey,
  activeTab,
  onTabChange,
  isVerified = true,
  onOpenUpload,
  onTriggerAI,
  isAiActive = false,
}) => {
  const currentProjectName =
    projectName ||
    projects.find((p) => p.id === activeProjectId)?.name ||
    "Default Project";

  return (
    <header
      style={{
        height: "48px",
        backgroundColor: "#FFFFFF",
        borderBottom: "1px solid #E2E8F0",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 14px",
        boxSizing: "border-box",
        zIndex: 20,
        userSelect: "none",
        gap: "12px",
        flexShrink: 0,
      }}
    >
      {/* 1. LEFT: Brand & Unified Hierarchy (Project / Layout / Level) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          minWidth: 0,
          flexShrink: 1,
        }}
      >
        {/* Brand Icon & Name */}
        <div style={{ display: "flex", alignItems: "center", gap: "7px", flexShrink: 0 }}>
          <div
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "4px",
              backgroundColor: "#2563EB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFFFFF",
              fontWeight: 800,
              fontSize: "0.8rem",
              letterSpacing: "-0.03em",
              flexShrink: 0,
            }}
          >
            L
          </div>
          <span
            style={{
              fontSize: "0.9rem",
              fontWeight: 700,
              color: "#0F172A",
              letterSpacing: "-0.01em",
              whiteSpace: "nowrap",
            }}
          >
            Layouts AI
          </span>
          <span
            style={{
              fontSize: "0.65rem",
              backgroundColor: "#F1F5F9",
              color: "#475569",
              padding: "2px 5px",
              borderRadius: "4px",
              fontWeight: 700,
              border: "1px solid #E2E8F0",
              whiteSpace: "nowrap",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            BIM 2D CAD
          </span>
        </div>

        {/* Vertical Divider */}
        <div
          style={{
            height: "16px",
            width: "1px",
            backgroundColor: "#E2E8F0",
            flexShrink: 0,
          }}
        />

        {/* Project Name Breadcrumb */}
        <button
          onClick={onOpenUpload}
          title={`Switch or open project: ${currentProjectName}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "5px",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "2px 4px",
            borderRadius: "4px",
            color: "#334155",
            fontSize: "0.82rem",
            fontWeight: 600,
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          <FolderOpen size={14} color="#64748B" />
          <span
            style={{
              maxWidth: "140px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {currentProjectName}
          </span>
          <span style={{ color: "#94A3B8", fontWeight: 400 }}>/</span>
        </button>

        {/* Layout / Floor Plan Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 700,
              color: "#64748B",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              whiteSpace: "nowrap",
            }}
          >
            Layout:
          </span>
          <select
            value={activeFloorPlanId || (availableFloorPlans[0]?.id || "")}
            onChange={(e) => {
              if (e.target.value === "__upload_new__") {
                onOpenUpload();
              } else if (onSwitchFloorPlan) {
                onSwitchFloorPlan(activeProjectId, e.target.value);
              }
            }}
            style={{
              height: "28px",
              backgroundColor: "#EFF6FF",
              border: "1px solid #93C5FD",
              borderRadius: "4px",
              padding: "0 8px",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "#1D4ED8",
              outline: "none",
              cursor: "pointer",
              maxWidth: "200px",
              whiteSpace: "nowrap",
              textOverflow: "ellipsis",
              boxSizing: "border-box",
            }}
          >
            {availableFloorPlans.length > 0 ? (
              availableFloorPlans.map((fp) => (
                <option key={fp.id} value={fp.id}>
                  📄 {fp.name}
                </option>
              ))
            ) : (
              <option value={activeFloorPlanId || "active"}>
                📄 {floorPlanName}
              </option>
            )}
            <option value="__upload_new__">➕ Import / Upload New Layout...</option>
          </select>
        </div>

        {/* Level / Storey Dropdown (co-located with Layout) */}
        {availableStoreys.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 700,
                color: "#64748B",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                whiteSpace: "nowrap",
              }}
            >
              Level:
            </span>
            <select
              value={activeStorey || availableStoreys[0]}
              onChange={(e) => onSwitchStorey && onSwitchStorey(e.target.value)}
              style={{
                height: "28px",
                backgroundColor: "#F8FAFC",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                padding: "0 8px",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "#1E293B",
                outline: "none",
                cursor: "pointer",
                maxWidth: "150px",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
                boxSizing: "border-box",
              }}
            >
              {availableStoreys.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 2. CENTER-RIGHT: Mode Switcher & Tools */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          flexShrink: 0,
        }}
      >
        {/* Segmented Mode Control */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            height: "30px",
            backgroundColor: "#F1F5F9",
            padding: "2px",
            borderRadius: "5px",
            border: "1px solid #E2E8F0",
            boxSizing: "border-box",
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => onTabChange("editor")}
            style={{
              height: "24px",
              backgroundColor: activeTab === "editor" ? "#FFFFFF" : "transparent",
              color: activeTab === "editor" ? "#0F172A" : "#64748B",
              border: "none",
              borderRadius: "3px",
              padding: "0 9px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: activeTab === "editor" ? "0 1px 2px rgba(0,0,0,0.06)" : "none",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            <Layers size={13} color={activeTab === "editor" ? "#2563EB" : "#64748B"} />
            <span>2D Drafting Editor</span>
          </button>

          <button
            onClick={() => onTabChange("diagnostics")}
            style={{
              height: "24px",
              backgroundColor: activeTab === "diagnostics" ? "#FFFFFF" : "transparent",
              color: activeTab === "diagnostics" ? "#0F172A" : "#64748B",
              border: "none",
              borderRadius: "3px",
              padding: "0 9px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: activeTab === "diagnostics" ? "0 1px 2px rgba(0,0,0,0.06)" : "none",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            <FileSpreadsheet size={13} color={activeTab === "diagnostics" ? "#2563EB" : "#64748B"} />
            <span>Diagnostics</span>
          </button>
        </div>

        {/* AI Space Planner Action Button */}
        {onTriggerAI && (
          <button
            onClick={onTriggerAI}
            style={{
              height: "30px",
              backgroundColor: isAiActive ? "#7C3AED" : "#F5F3FF",
              color: isAiActive ? "#FFFFFF" : "#7C3AED",
              border: `1px solid ${isAiActive ? "#7C3AED" : "#DDD6FE"}`,
              borderRadius: "5px",
              padding: "0 10px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              whiteSpace: "nowrap",
              flexShrink: 0,
              transition: "all 0.15s ease",
              boxSizing: "border-box",
            }}
          >
            <Sparkles size={13} color={isAiActive ? "#FFFFFF" : "#7C3AED"} />
            <span>AI Space Planner</span>
          </button>
        )}

        {/* Vertical Divider */}
        <div
          style={{
            height: "16px",
            width: "1px",
            backgroundColor: "#E2E8F0",
            flexShrink: 0,
          }}
        />

        {/* 3. FAR RIGHT: Status Badges */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            flexShrink: 0,
          }}
        >
          {isVerified ? (
            <div
              style={{
                height: "24px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "0.72rem",
                fontWeight: 600,
                color: "#166534",
                backgroundColor: "#F0FDF4",
                padding: "0 7px",
                borderRadius: "4px",
                border: "1px solid #BBF7D0",
                whiteSpace: "nowrap",
                boxSizing: "border-box",
                flexShrink: 0,
              }}
            >
              <CheckCircle2 size={12} color="#166534" />
              <span>IFC Verified</span>
            </div>
          ) : (
            <div
              style={{
                height: "24px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "0.72rem",
                fontWeight: 600,
                color: "#B45309",
                backgroundColor: "#FFFBEB",
                padding: "0 7px",
                borderRadius: "4px",
                border: "1px solid #FDE68A",
                whiteSpace: "nowrap",
                boxSizing: "border-box",
                flexShrink: 0,
              }}
            >
              <AlertTriangle size={12} color="#B45309" />
              <span>Verification Pending</span>
            </div>
          )}

          <span
            style={{
              fontSize: "0.72rem",
              color: "#94A3B8",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            Autosaved
          </span>
        </div>
      </div>
    </header>
  );
};
