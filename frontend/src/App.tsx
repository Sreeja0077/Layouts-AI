import React, { useEffect, useState } from "react";
import { GeometryVerificationReport } from "./types/verification";
import { VerificationHeader } from "./components/VerificationHeader";
import { GeometryPreviewCanvas } from "./components/GeometryPreviewCanvas";
import { VerificationSummaryPanel } from "./components/VerificationSummaryPanel";
import { RejectModal } from "./components/RejectModal";
import { LayoutCanvas } from "./editor/canvas";
import {
  fetchVerificationReport,
  verifyFloorPlan,
  rejectFloorPlan,
} from "./api/verification";

interface AppProps {
  projectId?: string;
  floorPlanId?: string;
}

export const App: React.FC<AppProps> = ({
  projectId = "proj_101",
  floorPlanId = "fp_501",
}) => {
  const [report, setReport] = useState<GeometryVerificationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"verification" | "editor">("verification");

  useEffect(() => {
    loadReport();
  }, [projectId, floorPlanId]);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVerificationReport(projectId, floorPlanId);
      setReport(data);
    } catch (err: any) {
      setError(err.message || "No verification report available for this floor plan.");
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!report) return;
    setIsProcessing(true);
    try {
      const updated = await verifyFloorPlan(projectId, floorPlanId);
      setReport(updated);
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
      const updated = await rejectFloorPlan(projectId, floorPlanId, reason);
      setReport(updated);
      setIsRejectModalOpen(false);
    } catch (err: any) {
      alert(`Rejection Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="canvas-container" style={{ color: "#38bdf8", fontSize: "1.125rem", padding: "2rem" }}>
        Loading floor plan geometry verification report...
      </div>
    );
  }

  return (
    <>
      {report && <VerificationHeader report={report} />}

      {/* Navigation View Switcher Bar */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          padding: "8px 24px",
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
        }}
      >
        <button
          onClick={() => setActiveTab("verification")}
          style={{
            backgroundColor: activeTab === "verification" ? "#0284c7" : "#1e293b",
            color: "#f8fafc",
            border: "1px solid #334155",
            borderRadius: "6px",
            padding: "6px 14px",
            fontWeight: 600,
            fontSize: "0.875rem",
            cursor: "pointer",
          }}
        >
          Verification View
        </button>
        <button
          onClick={() => setActiveTab("editor")}
          style={{
            backgroundColor: activeTab === "editor" ? "#0284c7" : "#1e293b",
            color: "#f8fafc",
            border: "1px solid #334155",
            borderRadius: "6px",
            padding: "6px 14px",
            fontWeight: 600,
            fontSize: "0.875rem",
            cursor: "pointer",
          }}
        >
          Konva 2D Canvas Editor (Task 5.2)
        </button>
      </div>

      {activeTab === "verification" && (
        <>
          {error || !report ? (
            <div className="canvas-container" style={{ flexDirection: "column", gap: "16px", padding: "2rem", alignItems: "center" }}>
              <div style={{ color: "#f87171", fontSize: "1.125rem", textAlign: "center" }}>
                {error || "No verification report available for this floor plan."}
              </div>
              <button className="btn-ctrl" onClick={loadReport}>
                Refresh Report
              </button>
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
          <LayoutCanvas />
        </main>
      )}
    </>
  );
};

export default App;
