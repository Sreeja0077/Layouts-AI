/**
 * Top Navigation Bar for Enterprise BIM Architectural Workstation.
 * Displays project branding, active storey level selector, view modes, AI layout trigger, and autosave status.
 */

import React from "react";
import {
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  Download,
  Save,
  FolderOpen,
} from "lucide-react";

export interface TopNavProps {
  projectName?: string;
  floorPlanName?: string;
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
  projectName = "Ashland Rev 2",
  floorPlanName = "Floor Plan 01",
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
  return (
    <header
      style={{
        height: "52px",
        backgroundColor: "#FFFFFF",
        borderBottom: "1px solid #D9DDE3",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        boxSizing: "border-box",
        zIndex: 20,
        userSelect: "none",
      }}
    >
      {/* Brand & Project Metadata */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              width: "26px",
              height: "26px",
              borderRadius: "4px",
              backgroundColor: "#2563EB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFFFFF",
              fontWeight: 800,
              fontSize: "0.85rem",
              letterSpacing: "-0.03em",
            }}
          >
            L
          </div>
          <span
            style={{
              fontSize: "0.95rem",
              fontWeight: 700,
              color: "#1F2937",
              letterSpacing: "-0.01em",
            }}
          >
            Layouts AI
          </span>
          <span
            style={{
              fontSize: "0.7rem",
              backgroundColor: "#F3F4F6",
              color: "#4B5563",
              padding: "2px 6px",
              borderRadius: "4px",
              fontWeight: 600,
              border: "1px solid #E5E7EB",
            }}
          >
            BIM 2D CAD
          </span>
        </div>

        <div
          style={{
            height: "18px",
            width: "1px",
            backgroundColor: "#D9DDE3",
          }}
        />

        {/* Project & Floor Plan Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={onOpenUpload}
            title="Switch or upload floor plans"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "4px 8px",
              borderRadius: "4px",
              color: "#374151",
              fontSize: "0.85rem",
              fontWeight: 600,
            }}
          >
            <FolderOpen size={14} color="#6B7280" />
            <span>{projectName}</span>
            <span style={{ color: "#9CA3AF", fontWeight: 400 }}>/</span>
            <span style={{ color: "#2563EB" }}>{floorPlanName}</span>
          </button>
        </div>
      </div>

      {/* BIM Level Selector & Mode Tabs */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* BIM Level Selector */}
        {availableStoreys.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Level:
            </span>
            <select
              value={activeStorey || availableStoreys[0]}
              onChange={(e) => onSwitchStorey && onSwitchStorey(e.target.value)}
              style={{
                backgroundColor: "#F9FAFB",
                border: "1px solid #D9DDE3",
                borderRadius: "4px",
                padding: "4px 10px",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "#1F2937",
                outline: "none",
                cursor: "pointer",
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

        <div style={{ height: "18px", width: "1px", backgroundColor: "#D9DDE3" }} />

        {/* View Mode Navigation Tabs */}
        <div
          style={{
            display: "flex",
            backgroundColor: "#F3F4F6",
            padding: "2px",
            borderRadius: "6px",
            border: "1px solid #E5E7EB",
          }}
        >
          <button
            onClick={() => onTabChange("editor")}
            style={{
              backgroundColor: activeTab === "editor" ? "#FFFFFF" : "transparent",
              color: activeTab === "editor" ? "#1F2937" : "#6B7280",
              border: "none",
              borderRadius: "4px",
              padding: "4px 12px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: activeTab === "editor" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Layers size={13} color={activeTab === "editor" ? "#2563EB" : "#6B7280"} />
            <span>2D Drafting Editor</span>
          </button>

          <button
            onClick={() => onTabChange("diagnostics")}
            style={{
              backgroundColor: activeTab === "diagnostics" ? "#FFFFFF" : "transparent",
              color: activeTab === "diagnostics" ? "#1F2937" : "#6B7280",
              border: "none",
              borderRadius: "4px",
              padding: "4px 12px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: activeTab === "diagnostics" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <FileSpreadsheet size={13} color={activeTab === "diagnostics" ? "#2563EB" : "#6B7280"} />
            <span>Diagnostics</span>
          </button>
        </div>

        {/* AI Space Planner Button */}
        {onTriggerAI && (
          <button
            onClick={onTriggerAI}
            style={{
              backgroundColor: isAiActive ? "#7C3AED" : "#F5F3FF",
              color: isAiActive ? "#FFFFFF" : "#7C3AED",
              border: "1px solid #DDD6FE",
              borderRadius: "4px",
              padding: "4px 12px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "all 0.15s ease",
            }}
          >
            <Sparkles size={13} color={isAiActive ? "#FFFFFF" : "#7C3AED"} />
            <span>AI Space Planner</span>
          </button>
        )}
      </div>

      {/* Status Badges & Quick Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {isVerified ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#15803D",
              backgroundColor: "#F0FDF4",
              padding: "3px 8px",
              borderRadius: "4px",
              border: "1px solid #DCFCE7",
            }}
          >
            <CheckCircle2 size={13} color="#15803D" />
            <span>IFC Verified</span>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#D97706",
              backgroundColor: "#FFFBEB",
              padding: "3px 8px",
              borderRadius: "4px",
              border: "1px solid #FEF3C7",
            }}
          >
            <AlertTriangle size={13} color="#D97706" />
            <span>Verification Pending</span>
          </div>
        )}

        <span style={{ fontSize: "0.75rem", color: "#9CA3AF" }}>Autosaved</span>
      </div>
    </header>
  );
};
