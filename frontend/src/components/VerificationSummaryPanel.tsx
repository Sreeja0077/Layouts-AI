import React from "react";
import { GeometryVerificationReport } from "../types/verification";

interface Props {
  report: GeometryVerificationReport;
  onVerify: () => void;
  onRejectClick: () => void;
  isProcessing: boolean;
}

export const VerificationSummaryPanel: React.FC<Props> = ({
  report,
  onVerify,
  onRejectClick,
  isProcessing,
}) => {
  const summary = report.elements_summary || {};
  const wallsCount = summary.walls ?? summary.WALL ?? 0;
  const doorsCount = summary.doors ?? summary.DOOR ?? 0;
  const windowsCount = summary.windows ?? summary.WINDOW ?? 0;
  const columnsCount = summary.columns ?? summary.COLUMN ?? 0;

  const criticalWarnings = report.warnings.filter((w) => w.severity === "CRITICAL");
  const canVerify = report.is_geometry_valid && criticalWarnings.length === 0;

  return (
    <aside className="side-panel">
      {/* Verification Metrics Section */}
      <div className="panel-section">
        <h3 className="section-title">Reconciliation Metrics</h3>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-value">{report.total_rooms_count}</div>
            <div className="metric-label">Valid Rooms / Spaces</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{report.total_net_area_sqm} m²</div>
            <div className="metric-label">Geometric Net Area</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{wallsCount}</div>
            <div className="metric-label">Structural Walls</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{doorsCount}</div>
            <div className="metric-label">Doors / Entrances</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{windowsCount}</div>
            <div className="metric-label">Windows</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{columnsCount}</div>
            <div className="metric-label">Columns</div>
          </div>
        </div>
      </div>

      {/* Geometry Warnings Section */}
      <div className="panel-section" style={{ flex: 1 }}>
        <h3 className="section-title">
          Anomalies & Warnings ({report.warnings.length})
        </h3>
        {report.warnings.length === 0 ? (
          <div style={{ color: "#4ade80", fontSize: "0.875rem" }}>
            ✓ Zero geometry anomalies detected. Floor plan geometry is valid.
          </div>
        ) : (
          report.warnings.map((w, idx) => (
            <div
              key={idx}
              className={`warning-card ${w.severity === "WARNING" ? "warning-level" : ""}`}
            >
              <div className="warning-header">
                <span className="warning-type">[{w.warning_type}]</span>
                <span style={{ fontSize: "0.7rem", color: w.severity === "CRITICAL" ? "#f87171" : "#fde047" }}>
                  {w.severity}
                </span>
              </div>
              <div className="warning-msg">{w.message}</div>
              {w.element_id && (
                <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "4px" }}>
                  Element: {w.element_id}
                </div>
              )}
            </div>
          ))
        )}

        {report.rejection_reason && (
          <div style={{ marginTop: "16px", padding: "12px", background: "rgba(239, 68, 68, 0.15)", borderRadius: "8px", border: "1px solid rgba(239, 68, 68, 0.4)" }}>
            <strong style={{ color: "#f87171", fontSize: "0.875rem" }}>Rejection Reason:</strong>
            <div style={{ fontSize: "0.8125rem", color: "#f8fafc", marginTop: "4px" }}>{report.rejection_reason}</div>
          </div>
        )}
      </div>

      {/* Bottom Actions Footer */}
      <div className="actions-footer">
        <button
          className="btn-verify"
          onClick={onVerify}
          disabled={!canVerify || isProcessing || report.verification_status === "VERIFIED"}
        >
          {report.verification_status === "VERIFIED" ? "✓ Verified" : "Verify Floor Plan"}
        </button>
        <button
          className="btn-reject"
          onClick={onRejectClick}
          disabled={isProcessing || report.verification_status === "REJECTED"}
        >
          {report.verification_status === "REJECTED" ? "Rejected" : "Reject"}
        </button>
      </div>
    </aside>
  );
};
