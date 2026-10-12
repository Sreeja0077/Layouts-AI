/**
 * Professional Enterprise BIM/CAD Application Shell for Layouts AI.
 * Combines TopNav, ProjectNavigator, LayoutCanvas, InspectorPanel, AILayoutPanel, and StatusBar.
 */

import React, { useState } from "react";
import { TopNav } from "./TopNav";
import { ProjectNavigator } from "./ProjectNavigator";
import { AILayoutPanel } from "./AILayoutPanel";
import { StatusBar } from "./StatusBar";
import { LayoutCanvas } from "../../editor/canvas/LayoutCanvas";
import { FloorPlanRenderModel } from "../../editor/renderer/renderTypes";
import { LayoutSuggestionPayload } from "../../api/layout";
import {
  submitRequirement,
  clarifyRequirement,
  RequirementAnalysisResponse,
} from "../../api/requirements";

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

  // Phase 8.5 Requirement AI State
  const [promptInput, setPromptInput] = useState<string>("6 Professional Desks + 1 Manager Cabin near the window");
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isClarifying, setIsClarifying] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<RequirementAnalysisResponse | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  const [candidates, setCandidates] = useState<LayoutSuggestionPayload[]>([]);
  const [activeCandidateIdx, setActiveCandidateIdx] = useState<number>(0);

  const handleAnalyzeRequirement = async () => {
    if (!promptInput.trim() || isAnalyzing) return;
    setIsAnalyzing(true);
    setAiError(null);
    try {
      const targetFpId = activeFloorPlanId || renderModel?.id || "fp_default";
      const targetProjId = activeProjectId || "proj_default";
      const res = await submitRequirement({
        raw_text: promptInput.trim(),
        project_id: targetProjId,
        floor_plan_id: targetFpId,
      });
      setAnalysisResult(res);
    } catch (err: any) {
      setAiError(err.message || "Failed to analyze requirement");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleClarifyRequirement = async (questionId: string, answer: string) => {
    if (!analysisResult || !answer.trim() || isClarifying) return;
    setIsClarifying(true);
    setAiError(null);
    try {
      const res = await clarifyRequirement(
        analysisResult.requirement_set_id,
        answer.trim(),
        questionId
      );
      setAnalysisResult(res);
    } catch (err: any) {
      setAiError(err.message || "Failed to submit clarification");
    } finally {
      setIsClarifying(false);
    }
  };

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
            onAnalyze={handleAnalyzeRequirement}
            isAnalyzing={isAnalyzing}
            analysisResult={analysisResult}
            error={aiError}
            onClarify={handleClarifyRequirement}
            isClarifying={isClarifying}
            candidates={candidates}
            activeCandidateIdx={activeCandidateIdx}
            onSelectCandidate={setActiveCandidateIdx}
            onClose={() => setIsAiPanelOpen(false)}
          />
        )}
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
