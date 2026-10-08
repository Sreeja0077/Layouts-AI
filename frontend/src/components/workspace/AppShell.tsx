/**
 * Professional Enterprise BIM/CAD Application Shell for Layouts AI.
 * Combines TopNav, ProjectNavigator, LayoutCanvas, InspectorPanel, AILayoutPanel, and StatusBar.
 */

import React, { useState } from "react";
import { TopNav } from "./TopNav";
import { ProjectNavigator } from "./ProjectNavigator";
import { InspectorPanel } from "./InspectorPanel";
import { AILayoutPanel } from "./AILayoutPanel";
import { StatusBar } from "./StatusBar";
import { LayoutCanvas } from "../../editor/canvas/LayoutCanvas";
import { FloorPlanRenderModel } from "../../editor/renderer/renderTypes";
import { LayoutSuggestionPayload } from "../../api/layout";

export interface AppShellProps {
  renderModel?: FloorPlanRenderModel;
  projectName?: string;
  projects?: Array<{ id: string; name: string }>;
  activeProjectId?: string;
  onSwitchProject?: (pId: string) => void;
  activeFloorPlanId?: string;
  availableFloorPlans?: Array<{ id: string; name: string }>;
  onSwitchFloorPlan?: (pId: string, fpId: string) => void;
  availableStoreys?: string[];
  activeStorey?: string;
  onSwitchStorey?: (storeyName: string) => void;
  onGoToUpload: () => void;
  activeTab: "workspace" | "editor" | "diagnostics";
  onTabChange: (tab: "workspace" | "editor" | "diagnostics") => void;
  isVerified?: boolean;
}

export const AppShell: React.FC<AppShellProps> = ({
  renderModel,
  projectName,
  projects = [],
  activeProjectId,
  onSwitchProject,
  activeFloorPlanId,
  availableFloorPlans = [],
  onSwitchFloorPlan,
  availableStoreys = [],
  activeStorey,
  onSwitchStorey,
  onGoToUpload,
  activeTab,
  onTabChange,
  isVerified = true,
}) => {
  const [isNavCollapsed, setIsNavCollapsed] = useState<boolean>(false);
  const [isAiPanelOpen, setIsAiPanelOpen] = useState<boolean>(false);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);

  // AI Layout Solver State
  const [promptInput, setPromptInput] = useState<string>("6 Professional Desks + 1 Manager Cabin");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [candidates, setCandidates] = useState<LayoutSuggestionPayload[]>([]);
  const [activeCandidateIdx, setActiveCandidateIdx] = useState<number>(0);

  const totalElements =
    (renderModel?.walls?.length || 0) +
    (renderModel?.doors?.length || 0) +
    (renderModel?.windows?.length || 0) +
    (renderModel?.columns?.length || 0) +
    (renderModel?.spaces?.length || 0) +
    (renderModel?.furniture?.length || 0);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100vw",
        backgroundColor: "#F5F6F8",
        overflow: "hidden",
      }}
    >
      {/* 1. TOP NAVIGATION BAR */}
      <TopNav
        projectName={projectName}
        projects={projects}
        activeProjectId={activeProjectId}
        onSwitchProject={onSwitchProject}
        floorPlanName={renderModel?.name || "Executive Suite"}
        availableFloorPlans={availableFloorPlans}
        activeFloorPlanId={activeFloorPlanId}
        onSwitchFloorPlan={onSwitchFloorPlan}
        availableStoreys={availableStoreys}
        activeStorey={activeStorey}
        onSwitchStorey={onSwitchStorey}
        activeTab={activeTab}
        onTabChange={onTabChange}
        isVerified={isVerified}
        onOpenUpload={onGoToUpload}
        onTriggerAI={() => setIsAiPanelOpen((prev) => !prev)}
        isAiActive={isAiPanelOpen}
      />

      {/* 2. MAIN WORKSPACE BODY */}
      <div style={{ flex: 1, display: "flex", position: "relative", overflow: "hidden" }}>
        {/* LEFT MODEL NAVIGATOR */}
        <ProjectNavigator
          renderModel={renderModel}
          availableStoreys={availableStoreys}
          activeStorey={activeStorey}
          onSelectStorey={onSwitchStorey}
          availableFloorPlans={availableFloorPlans}
          activeFloorPlanId={activeFloorPlanId}
          onSelectFloorPlan={onSwitchFloorPlan}
          isCollapsed={isNavCollapsed}
          onToggleCollapse={() => setIsNavCollapsed((prev) => !prev)}
        />

        {/* CENTER CAD CANVAS */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
          <LayoutCanvas
            renderModel={renderModel}
            activeFloorPlanId={activeFloorPlanId}
            availableFloorPlans={availableFloorPlans}
            onSwitchFloorPlan={onSwitchFloorPlan}
            availableStoreys={availableStoreys}
            activeStorey={activeStorey}
            onSwitchStorey={onSwitchStorey}
            onGoToUpload={onGoToUpload}
          />
        </main>

        {/* RIGHT AI SPACE PLANNER PANEL (SLIDE IN) */}
        {isAiPanelOpen && (
          <AILayoutPanel
            promptInput={promptInput}
            onPromptChange={setPromptInput}
            onGenerate={() => {}}
            isGenerating={isGenerating}
            candidates={candidates}
            activeCandidateIdx={activeCandidateIdx}
            onSelectCandidate={setActiveCandidateIdx}
            onClose={() => setIsAiPanelOpen(false)}
          />
        )}

        {/* RIGHT PROPERTIES INSPECTOR */}
        <InspectorPanel
          renderModel={renderModel}
          selectedObjectId={selectedObjectId}
          onClearSelection={() => setSelectedObjectId(null)}
        />
      </div>

      {/* 3. BOTTOM STATUS BAR */}
      <StatusBar
        activeStorey={activeStorey || availableStoreys[0] || "Grade Level"}
        totalElements={totalElements}
        selectedObjectId={selectedObjectId}
      />
    </div>
  );
};
