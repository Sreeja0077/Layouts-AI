import React from "react";
import { GeometryVerificationReport } from "../types/verification";

interface Props {
  report: GeometryVerificationReport;
}

export const VerificationHeader: React.FC<Props> = ({ report }) => {
  const statusClass =
    report.verification_status === "VERIFIED"
      ? "badge-verified"
      : report.verification_status === "REJECTED"
      ? "badge-rejected"
      : "badge-pending";

  const sourceClass = report.source_type === "IFC" ? "badge-ifc" : "badge-dxf";

  return (
    <header className="header">
      <div className="header-title">
        <span>📐</span>
        <span>Layouts Team Floor Plan Verification</span>
        <span style={{ color: "#94a3b8", fontWeight: 400 }}>|</span>
        <span style={{ color: "#38bdf8" }}>{report.floor_plan_name}</span>
      </div>

      <div className="header-meta">
        <span className={`badge ${sourceClass}`}>{report.source_type}</span>
        <span className={`badge ${statusClass}`}>{report.verification_status}</span>
        <div className="user-pill">
          <span>👤 Reviewer:</span>
          <strong style={{ color: "#e2e8f0" }}>
            {report.reviewer_user_id || "Layouts Team Reviewer (dev_user@company.com)"}
          </strong>
        </div>
      </div>
    </header>
  );
};
