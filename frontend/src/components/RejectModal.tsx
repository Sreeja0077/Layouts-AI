import React, { useState } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => void;
  isProcessing: boolean;
}

export const RejectModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  isProcessing,
}) => {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Rejection reason comment is required.");
      return;
    }
    setError("");
    onSubmit(reason.trim());
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <h3 className="modal-title">Reject Floor Plan Geometry</h3>
        <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "16px" }}>
          Please provide a detailed explanation for why this floor plan geometry is being rejected.
          This comment will be recorded in the audit log for the client team.
        </p>

        <form onSubmit={handleSubmit}>
          <textarea
            className="modal-textarea"
            placeholder="Enter mandatory rejection reason (e.g. Unclosed exterior walls, incorrect room boundary topology, missing entrance doors)..."
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError("");
            }}
          />

          {error && (
            <div style={{ color: "#f87171", fontSize: "0.8125rem", marginBottom: "12px" }}>
              {error}
            </div>
          )}

          <div className="modal-actions">
            <button
              type="button"
              className="btn-ctrl"
              onClick={onClose}
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-reject"
              disabled={isProcessing || !reason.trim()}
              style={{ flex: "none", padding: "8px 16px" }}
            >
              {isProcessing ? "Submitting..." : "Confirm Rejection"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
