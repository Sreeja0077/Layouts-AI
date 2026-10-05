import React, { useEffect, useState } from "react";
import { GeometryVerificationReport } from "./types/verification";
import { VerificationHeader } from "./components/VerificationHeader";
import { GeometryPreviewCanvas } from "./components/GeometryPreviewCanvas";
import { VerificationSummaryPanel } from "./components/VerificationSummaryPanel";
import { RejectModal } from "./components/RejectModal";
import {
  fetchVerificationReport,
  verifyFloorPlan,
  rejectFloorPlan,
} from "./api/verification";

export const App: React.FC = () => {
  const [report, setReport] = useState<GeometryVerificationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVerificationReport();
      setReport(data);
    } catch (err: any) {
      setError(err.message || "Failed to load floor plan verification report");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!report) return;
    setIsProcessing(true);
    try {
      const updated = await verifyFloorPlan();
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
      const updated = await rejectFloorPlan("proj_101", "fp_501", reason);
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
      <div className="canvas-container" style={{ color: "#38bdf8", fontSize: "1.125rem" }}>
        Loading floor plan geometry verification report...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="canvas-container" style={{ flexDirection: "column", gap: "16px" }}>
        <div style={{ color: "#f87171", fontSize: "1.125rem" }}>
          Error: {error || "Verification report unavailable"}
        </div>
        <button className="btn-ctrl" onClick={loadReport}>Retry Loading</button>
      </div>
    );
  }

  return (
    <>
      <VerificationHeader report={report} />
      <main className="main-content">
        <GeometryPreviewCanvas report={report} />
        <VerificationSummaryPanel
          report={report}
          onVerify={handleVerify}
          onRejectClick={() => setIsRejectModalOpen(true)}
          isProcessing={isProcessing}
        />
      </main>

      <RejectModal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        onSubmit={handleRejectSubmit}
        isProcessing={isProcessing}
      />
    </>
  );
};

export default App;
