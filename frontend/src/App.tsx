import React, { useEffect, useState } from "react";
import { GeometryVerificationReport } from "./types/verification";
import { VerificationHeader } from "./components/VerificationHeader";
import { GeometryPreviewCanvas } from "./components/GeometryPreviewCanvas";
import { VerificationSummaryPanel } from "./components/VerificationSummaryPanel";
import { RejectModal } from "./components/RejectModal";
import {
  fetchVerificationReport,
  ingestFloorPlan,
  verifyFloorPlan,
  rejectFloorPlan,
} from "./api/verification";

export const App: React.FC = () => {
  const [report, setReport] = useState<GeometryVerificationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<string>("sample_floor_plan.dxf");

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
      // If report not found, attempt auto-ingesting sample DXF for initial view
      try {
        const ingested = await ingestFloorPlan("proj_101", selectedFile, "fp_501");
        setReport(ingested);
      } catch (ingestErr: any) {
        setError(ingestErr.message || "Failed to load floor plan verification report");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleIngestNewFile = async (fileName: string) => {
    setLoading(true);
    setError(null);
    setSelectedFile(fileName);
    try {
      const ingested = await ingestFloorPlan("proj_101", fileName, "fp_501");
      setReport(ingested);
    } catch (err: any) {
      setError(err.message || `Failed to ingest '${fileName}'`);
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
      <div className="canvas-container" style={{ color: "#38bdf8", fontSize: "1.125rem", padding: "2rem" }}>
        Loading floor plan geometry verification report...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="canvas-container" style={{ flexDirection: "column", gap: "16px", padding: "2rem", alignItems: "center" }}>
        <div style={{ color: "#f87171", fontSize: "1.125rem" }}>
          {error || "No active verification report found."}
        </div>
        <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
          <button className="btn-ctrl" onClick={() => handleIngestNewFile("sample_floor_plan.dxf")}>
            Ingest Sample DXF
          </button>
          <button className="btn-ctrl" onClick={() => handleIngestNewFile("4420 Ashland Rev 2.ifc")}>
            Ingest Ashland IFC
          </button>
        </div>
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
