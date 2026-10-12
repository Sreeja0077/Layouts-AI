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
import {
  generateLayoutCandidates,
  applySuggestionToRenderModel,
  LayoutSuggestionPayload,
  InfeasibilityReportPayload,
} from "../../api/layout";
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

  // Active floor plan render model (preserves updates when candidate layout is previewed)
  const [activeModel, setActiveModel] = useState<FloorPlanRenderModel | undefined>(renderModel);

  // Synchronize when external renderModel changes
  React.useEffect(() => {
    setActiveModel(renderModel);
  }, [renderModel]);

  // Phase 8.5 Requirement AI State
  const [promptInput, setPromptInput] = useState<string>("6 Professional Desks + 1 Manager Cabin near the window");
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isClarifying, setIsClarifying] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<RequirementAnalysisResponse | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // Phase 9 Layout Generation State
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [candidates, setCandidates] = useState<LayoutSuggestionPayload[]>([]);
  const [activeCandidateIdx, setActiveCandidateIdx] = useState<number>(0);
  const [infeasibilityReport, setInfeasibilityReport] = useState<InfeasibilityReportPayload | null>(null);
  const [selectedRegionPoints, setSelectedRegionPoints] = useState<Array<{ x: number; y: number }> | null>(null);

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

  const handleGenerateLayoutCandidates = async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    setAiError(null);
    setInfeasibilityReport(null);

    try {
      const targetFpId = activeFloorPlanId || renderModel?.id || "fp_501";

      // 1. Determine requirement items from Phase 8 analysisResult or fallback
      let reqs: any[] = [];
      if (analysisResult?.requirement_set?.items) {
        reqs = analysisResult.requirement_set.items
          .filter((it) => it.quantity > 0)
          .map((it) => ({
            item_type: it.semantic_type || it.raw_phrase,
            quantity: it.quantity,
          }));
      }

      if (reqs.length === 0) {
        let profQty = 2;
        let mgrQty = 1;
        const profMatch = promptInput.match(/(\d+)\s*(?:professional|desk|workstation)/i);
        if (profMatch) profQty = parseInt(profMatch[1]);
        const mgrMatch = promptInput.match(/(\d+)\s*(?:manager|executive|cabin)/i);
        if (mgrMatch) mgrQty = parseInt(mgrMatch[1]);
        reqs = [
          { item_type: "PROFESSIONAL_DESK", quantity: profQty },
          { item_type: "MANAGER_DESK", quantity: mgrQty },
        ];
      }

      // 2. Map existing layout objects from canvas
      const currentFurniture = (activeModel || renderModel)?.furniture || [];
      const mappedFurniture = currentFurniture.map((f) => ({
        id: f.id,
        catalog_item_id: f.catalogItemId || f.itemType,
        item_type: f.itemType,
        position: f.position,
        rotation: f.rotationDeg,
        width: f.widthMeters,
        height: f.depthMeters,
        isLocked: f.isLocked || false,
        movability_status: f.isLocked ? "SOLD_FIXED" : "AVAILABLE_MOVABLE",
      }));

      // 3. Call backend POST /api/v1/layouts/generate
      const res = await generateLayoutCandidates({
        floor_plan_id: targetFpId,
        storey_name: activeStorey,
        requirements: reqs,
        selected_region_polygon: selectedRegionPoints || undefined,
        existing_furniture: mappedFurniture,
      });

      setCandidates(res.candidates || []);
      setInfeasibilityReport(res.infeasibility_report || null);

      if (res.candidates && res.candidates.length > 0) {
        setActiveCandidateIdx(0);
        const base = renderModel || activeModel;
        if (base) {
          setActiveModel(applySuggestionToRenderModel(base, res.candidates[0]));
        }
      }
    } catch (err: any) {
      setAiError(err.message || "Failed to generate layout configurations");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectCandidate = (idx: number) => {
    setActiveCandidateIdx(idx);
    if (candidates[idx]) {
      const base = renderModel || activeModel;
      if (base) {
        setActiveModel(applySuggestionToRenderModel(base, candidates[idx]));
      }
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
            renderModel={activeModel || renderModel}
            activeFloorPlanId={activeFloorPlanId}
            availableFloorPlans={availableFloorPlans}
            onSwitchFloorPlan={onSwitchFloorPlan}
            availableStoreys={availableStoreys}
            activeStorey={activeStorey}
            onSwitchStorey={onSwitchStorey}
            onGoToUpload={onGoToUpload}
            onRegionChange={setSelectedRegionPoints}
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
            onGenerateLayout={handleGenerateLayoutCandidates}
            isGenerating={isGenerating}
            infeasibilityReport={infeasibilityReport}
            candidates={candidates}
            activeCandidateIdx={activeCandidateIdx}
            onSelectCandidate={handleSelectCandidate}
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
