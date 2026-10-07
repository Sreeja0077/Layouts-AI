import React, { useEffect, useState } from "react";
import { GeometryVerificationReport } from "./types/verification";
import { VerificationHeader } from "./components/VerificationHeader";
import { GeometryPreviewCanvas } from "./components/GeometryPreviewCanvas";
import { VerificationSummaryPanel } from "./components/VerificationSummaryPanel";
import { RejectModal } from "./components/RejectModal";
import { FloorPlanUploadPanel } from "./components/FloorPlanUploadPanel";
import { LayoutCanvas } from "./editor/canvas";
import {
  fetchVerificationReport,
  verifyFloorPlan,
  rejectFloorPlan,
} from "./api/verification";
import {
  publishFloorPlanVersion,
  reportToRenderModel,
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
  const [activeProjectId, setActiveProjectId] = useState<string>(initialProjectId);
  const [activeFloorPlanId, setActiveFloorPlanId] = useState<string>(initialFloorPlanId);

  const [report, setReport] = useState<GeometryVerificationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [isRejectModalOpen, setIsRejectModalOpen] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"upload" | "verification" | "editor">("upload");

  const [editorRenderModel, setEditorRenderModel] = useState<FloorPlanRenderModel | undefined>(undefined);

  useEffect(() => {
    loadReport(activeProjectId, activeFloorPlanId);
  }, [activeProjectId, activeFloorPlanId]);

  const loadReport = async (pId: string, fpId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVerificationReport(pId, fpId);
      setReport(data);
      setEditorRenderModel(reportToRenderModel(data));
    } catch (err: any) {
      setError(err.message || "No verification report available for this floor plan.");
      setReport(null);
      setEditorRenderModel(undefined);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = (res: IngestionStatusResponse) => {
    setActiveProjectId(res.project_id);
    setActiveFloorPlanId(res.floor_plan_id);

    if (res.verification_report) {
      setReport(res.verification_report);
      setEditorRenderModel(reportToRenderModel(res.verification_report));
    } else {
      loadReport(res.project_id, res.floor_plan_id);
    }

    // Auto-switch to verification review view
    setActiveTab("verification");
  };

  const handleVerify = async () => {
    if (!report) return;
    setIsProcessing(true);
    try {
      const updated = await verifyFloorPlan(activeProjectId, activeFloorPlanId);
      setReport(updated);
      setEditorRenderModel(reportToRenderModel(updated));
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
      setReport(updated);
      setEditorRenderModel(reportToRenderModel(updated));
      setIsRejectModalOpen(false);
    } catch (err: any) {
      alert(`Rejection Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePublish = async () => {
    if (!report) return;
    setIsProcessing(true);
    try {
      await publishFloorPlanVersion(activeProjectId, activeFloorPlanId);
      alert(`Floor Plan baseline published successfully! Navigating to 2D Editor.`);
      setActiveTab("editor");
    } catch (err: any) {
      alert(`Publishing Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <>
      {report && <VerificationHeader report={report} />}

      {/* Product Flow Navigation Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          padding: "10px 24px",
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
        }}
      >
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => setActiveTab("upload")}
            style={{
              backgroundColor: activeTab === "upload" ? "#0284c7" : "#1e293b",
              color: "#f8fafc",
              border: "1px solid #334155",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            1. Upload Floor Plan (Task 2.5)
          </button>
          <button
            onClick={() => setActiveTab("verification")}
            style={{
              backgroundColor: activeTab === "verification" ? "#0284c7" : "#1e293b",
              color: "#f8fafc",
              border: "1px solid #334155",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            2. Layouts Team Verification
          </button>
          <button
            onClick={() => setActiveTab("editor")}
            style={{
              backgroundColor: activeTab === "editor" ? "#0284c7" : "#1e293b",
              color: "#f8fafc",
              border: "1px solid #334155",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            3. 2D Editor & Freehand Region (Task 5.4, 6.1, 6.2)
          </button>
        </div>

        {report?.verification_status === "VERIFIED" && (
          <button
            onClick={handlePublish}
            disabled={isProcessing}
            style={{
              backgroundColor: "#16a34a",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              padding: "8px 16px",
              fontWeight: 700,
              fontSize: "0.875rem",
              cursor: isProcessing ? "not-allowed" : "pointer",
            }}
          >
            {isProcessing ? "Publishing..." : "✓ Publish Version Baseline"}
          </button>
        )}
      </div>

      {activeTab === "upload" && (
        <main className="main-content" style={{ padding: "32px 16px" }}>
          <FloorPlanUploadPanel onUploadSuccess={handleUploadSuccess} />
        </main>
      )}

      {activeTab === "verification" && (
        <>
          {loading ? (
            <div className="canvas-container" style={{ color: "#38bdf8", fontSize: "1.125rem", padding: "2rem" }}>
              Loading floor plan geometry verification report...
            </div>
          ) : error || !report ? (
            <div className="canvas-container" style={{ flexDirection: "column", gap: "16px", padding: "2rem", alignItems: "center" }}>
              <div style={{ color: "#f87171", fontSize: "1.125rem", textAlign: "center" }}>
                {error || "No verification report available for this floor plan."}
              </div>
              <div style={{ display: "flex", gap: "12px" }}>
                <button className="btn-ctrl" onClick={() => loadReport(activeProjectId, activeFloorPlanId)}>
                  Refresh Report
                </button>
                <button className="btn-ctrl" onClick={() => setActiveTab("upload")}>
                  Upload New Floor Plan
                </button>
              </div>
            </div>
          ) : (
            <main className="main-content">
              <GeometryPreviewCanvas report={report} />
              <VerificationSummaryPanel
                report={report}
                onVerify={handleVerify}
                onRejectClick={() => setIsRejectModalOpen(true)}
                isProcessing={isProcessing}
              />
            </main>
          )}

          <RejectModal
            isOpen={isRejectModalOpen}
            onClose={() => setIsRejectModalOpen(false)}
            onSubmit={handleRejectSubmit}
            isProcessing={isProcessing}
          />
        </>
      )}

      {activeTab === "editor" && (
        <main className="main-content" style={{ padding: "16px", display: "flex", flexDirection: "column", height: "calc(100vh - 120px)" }}>
          <LayoutCanvas renderModel={editorRenderModel} />
        </main>
      )}
    </>
  );
};

export default App;
