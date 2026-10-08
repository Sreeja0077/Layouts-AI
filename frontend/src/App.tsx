import React, { useEffect, useState } from "react";
import { GeometryVerificationReport } from "./types/verification";
import { VerificationHeader } from "./components/VerificationHeader";
import { GeometryPreviewCanvas } from "./components/GeometryPreviewCanvas";
import { VerificationSummaryPanel } from "./components/VerificationSummaryPanel";
import { RejectModal } from "./components/RejectModal";
import { FloorPlanUploadPanel } from "./components/FloorPlanUploadPanel";
import { LayoutCanvas } from "./editor/canvas";
import { AppShell } from "./components/workspace/AppShell";
import {
  fetchVerificationReport,
  verifyFloorPlan,
  rejectFloorPlan,
} from "./api/verification";
import {
  reportToRenderModel,
  fetchIngestionStatus,
  listFloorPlans,
  IngestionStatusResponse,
} from "./api/ingestion";
import { FloorPlanRenderModel } from "./editor/renderer/renderTypes";

interface AppProps {
  projectId?: string;
  floorPlanId?: string;
}

export const App: React.FC<AppProps> = ({
  projectId: initialProjectId = "proj_101",
  floorPlanId: initialFloorPlanId = "fp_501",
}) => {
  const [activeProjectId, setActiveProjectId] = useState<string>(() => {
    return localStorage.getItem("layouts_ai_active_project_id") || initialProjectId;
  });
  const [activeFloorPlanId, setActiveFloorPlanId] = useState<string>(() => {
    return localStorage.getItem("layouts_ai_active_floor_plan_id") || initialFloorPlanId;
  });

  const [report, setReport] = useState<GeometryVerificationReport | null>(null);
  const [activeStorey, setActiveStorey] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [isRejectModalOpen, setIsRejectModalOpen] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"workspace" | "editor" | "diagnostics">(() => {
    const saved = localStorage.getItem("layouts_ai_active_tab");
    return (saved as any) || "workspace";
  });

  const [editorRenderModel, setEditorRenderModel] = useState<FloorPlanRenderModel | undefined>(undefined);

  const [userFloorPlans, setUserFloorPlans] = useState<Array<{ id: string; name: string }>>([]);

  const resolveStoreyForReport = (
    data: GeometryVerificationReport,
    preferred?: string
  ): string | undefined => {
    const names = (data.available_storeys || [])
      .map((item) => item.name)
      .filter(Boolean);

    if (preferred && names.includes(preferred)) return preferred;
    if (data.recommended_storey && names.includes(data.recommended_storey)) {
      return data.recommended_storey;
    }
    return names[0];
  };

  const applyReportToEditor = (
    data: GeometryVerificationReport,
    preferredStorey?: string
  ) => {
    const chosenStorey = resolveStoreyForReport(data, preferredStorey);
    setReport(data);
    setActiveStorey(chosenStorey);
    setEditorRenderModel(reportToRenderModel(data, chosenStorey));
  };

  const handleStoreyChange = (storeyName: string) => {
    setActiveStorey(storeyName);
    if (report) {
      setEditorRenderModel(reportToRenderModel(report, storeyName));
    }
  };

  useEffect(() => {
    if (activeProjectId) {
      listFloorPlans(activeProjectId)
        .then((fps) => {
          const clean = fps.filter(
            (fp) =>
              !fp.name.toLowerCase().includes("sample_floor_plan") &&
              !fp.name.toLowerCase().includes("test plan") &&
              fp.id !== "fp_501"
          );
          setUserFloorPlans(clean.map((f) => ({ id: f.id, name: f.name })));
        })
        .catch(() => {});
    }
  }, [activeProjectId]);

  useEffect(() => {
    if (activeProjectId) localStorage.setItem("layouts_ai_active_project_id", activeProjectId);
  }, [activeProjectId]);

  useEffect(() => {
    if (activeFloorPlanId) localStorage.setItem("layouts_ai_active_floor_plan_id", activeFloorPlanId);
  }, [activeFloorPlanId]);

  useEffect(() => {
    if (activeTab) localStorage.setItem("layouts_ai_active_tab", activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (activeProjectId && activeFloorPlanId) {
      loadReport(activeProjectId, activeFloorPlanId);
    }
  }, [activeProjectId, activeFloorPlanId]);

  const loadReport = async (pId: string, fpId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVerificationReport(pId, fpId);
      applyReportToEditor(data, activeStorey);
    } catch (err: any) {
      // If primary report load fails (e.g. initial demo fp_501 purged), load latest user floor plan for project
      try {
        const fps = await listFloorPlans(pId);
        if (fps && fps.length > 0) {
          const latestFp = fps[fps.length - 1];
          setActiveFloorPlanId(latestFp.id);
          const data = await fetchVerificationReport(pId, latestFp.id);
          applyReportToEditor(data, activeStorey);
          return;
        }
      } catch {
        // Ignored fallback
      }
      setError(err.message || "No verification report available for this floor plan.");
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenEditor = (res: IngestionStatusResponse) => {
    setActiveProjectId(res.project_id);
    setActiveFloorPlanId(res.floor_plan_id);
    localStorage.setItem("layouts_ai_active_project_id", res.project_id);
    localStorage.setItem("layouts_ai_active_floor_plan_id", res.floor_plan_id);
    localStorage.setItem("layouts_ai_active_tab", "editor");

    listFloorPlans(res.project_id)
      .then((fps) => {
        const clean = fps.filter(
          (fp) =>
            !fp.name.toLowerCase().includes("sample_floor_plan") &&
            !fp.name.toLowerCase().includes("test plan") &&
            fp.id !== "fp_501"
        );
        setUserFloorPlans(clean.map((f) => ({ id: f.id, name: f.name })));
      })
      .catch(() => {});

    if (res.verification_report) {
      applyReportToEditor(res.verification_report, activeStorey);
    } else {
      loadReport(res.project_id, res.floor_plan_id);
    }

    // Direct transition to 2D Canvas Editor
    setActiveTab("editor");
  };

  const handleOpenExistingFloorPlan = async (pId: string, fpId: string) => {
    setActiveProjectId(pId);
    setActiveFloorPlanId(fpId);
    localStorage.setItem("layouts_ai_active_project_id", pId);
    localStorage.setItem("layouts_ai_active_floor_plan_id", fpId);
    localStorage.setItem("layouts_ai_active_tab", "editor");
    setLoading(true);
    try {
      const res = await fetchIngestionStatus(pId, fpId);
      if (res.verification_report) {
        applyReportToEditor(res.verification_report, activeStorey);
      } else {
        await loadReport(pId, fpId);
      }
    } catch {
      await loadReport(pId, fpId);
    } finally {
      setLoading(false);
      setActiveTab("editor");
    }
  };

  const handleVerify = async () => {
    if (!report) return;
    setIsProcessing(true);
    try {
      const updated = await verifyFloorPlan(activeProjectId, activeFloorPlanId);
      applyReportToEditor(updated, activeStorey);
    } catch (err: any) {
      alert(`Verification Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectSubmit = async (reason: string) => {
    if (!report) return;
    setIsProcessing(true);
    try {
      const updated = await rejectFloorPlan(activeProjectId, activeFloorPlanId, reason);
      applyReportToEditor(updated, activeStorey);
      setIsRejectModalOpen(false);
    } catch (err: any) {
      alert(`Rejection Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#020617", color: "#f8fafc", display: "flex", flexDirection: "column" }}>
      {/* Layouts AI Product Shell Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 28px",
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "6px",
                background: "linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                color: "#ffffff",
                fontSize: "0.875rem",
              }}
            >
              L
            </div>
            <span style={{ fontSize: "1.125rem", fontWeight: 700, letterSpacing: "-0.02em", color: "#f8fafc" }}>
              Layouts AI
            </span>
            <span style={{ fontSize: "0.75rem", backgroundColor: "#1e293b", color: "#94a3b8", padding: "2px 8px", borderRadius: "4px", fontWeight: 600 }}>
              Architectural Workstation
            </span>
          </div>
        </div>

        {/* Workspace Mode Navigation Bar */}
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            onClick={() => setActiveTab("workspace")}
            style={{
              backgroundColor: activeTab === "workspace" ? "#0284c7" : "transparent",
              color: activeTab === "workspace" ? "#ffffff" : "#94a3b8",
              border: "none",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            Floor Plans & Ingestion
          </button>
          <button
            onClick={() => setActiveTab("editor")}
            style={{
              backgroundColor: activeTab === "editor" ? "#0284c7" : "transparent",
              color: activeTab === "editor" ? "#ffffff" : "#94a3b8",
              border: "none",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            2D Canvas Editor
          </button>
          <button
            onClick={() => setActiveTab("diagnostics")}
            style={{
              backgroundColor: activeTab === "diagnostics" ? "#0284c7" : "transparent",
              color: activeTab === "diagnostics" ? "#ffffff" : "#94a3b8",
              border: "none",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            Technical Diagnostics
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      {activeTab === "workspace" && (
        <main style={{ padding: "28px 36px", flex: 1, display: "flex", flexDirection: "column", boxSizing: "border-box", width: "100%" }}>
          <FloorPlanUploadPanel
            onOpenEditor={handleOpenEditor}
            onOpenExistingFloorPlan={handleOpenExistingFloorPlan}
          />
        </main>
      )}

      {activeTab === "editor" && (
        <AppShell
          renderModel={editorRenderModel}
          activeFloorPlanId={activeFloorPlanId}
          availableFloorPlans={userFloorPlans}
          onSwitchFloorPlan={handleOpenExistingFloorPlan}
          availableStoreys={(report?.available_storeys || []).map((storey) => storey.name)}
          activeStorey={activeStorey}
          onSwitchStorey={handleStoreyChange}
          onGoToUpload={() => setActiveTab("workspace")}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          isVerified={Boolean(report?.verification_status === "VERIFIED")}
        />
      )}

      {activeTab === "diagnostics" && (
        <main style={{ padding: "16px", display: "flex", flexDirection: "column", flex: 1 }}>
          {report && <VerificationHeader report={report} />}
          {loading ? (
            <div className="canvas-container" style={{ color: "#38bdf8", fontSize: "1.125rem", padding: "2rem" }}>
              Loading technical geometry diagnostics...
            </div>
          ) : error || !report ? (
            <div className="canvas-container" style={{ flexDirection: "column", gap: "16px", padding: "2rem", alignItems: "center" }}>
              <div style={{ color: "#f87171", fontSize: "1.125rem", textAlign: "center" }}>
                {error || "No technical diagnostics available."}
              </div>
            </div>
          ) : (
            <div className="main-content">
              <GeometryPreviewCanvas report={report} />
              <VerificationSummaryPanel
                report={report}
                onVerify={handleVerify}
                onRejectClick={() => setIsRejectModalOpen(true)}
                isProcessing={isProcessing}
              />
            </div>
          )}

          <RejectModal
            isOpen={isRejectModalOpen}
            onClose={() => setIsRejectModalOpen(false)}
            onSubmit={handleRejectSubmit}
            isProcessing={isProcessing}
          />
        </main>
      )}
    </div>
  );
};

export default App;
