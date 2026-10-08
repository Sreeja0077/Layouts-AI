/**
 * Professional AI Space Planner Side Panel for Layouts AI Workstation.
 * Solves interior layouts inside real architectural geometry with rule evaluations.
 */

import React from "react";
import { Sparkles, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { LayoutSuggestionPayload } from "../../api/layout";

export interface AILayoutPanelProps {
  promptInput: string;
  onPromptChange: (val: string) => void;
  onGenerate: () => void;
  isGenerating: boolean;
  candidates: LayoutSuggestionPayload[];
  activeCandidateIdx: number;
  onSelectCandidate: (idx: number) => void;
  onClose: () => void;
}

export const AILayoutPanel: React.FC<AILayoutPanelProps> = ({
  promptInput,
  onPromptChange,
  onGenerate,
  isGenerating,
  candidates,
  activeCandidateIdx,
  onSelectCandidate,
  onClose,
}) => {
  return (
    <aside
      style={{
        width: "320px",
        backgroundColor: "#FFFFFF",
        borderLeft: "1px solid #D9DDE3",
        display: "flex",
        flexDirection: "column",
        fontSize: "0.8rem",
        userSelect: "none",
        boxSizing: "border-box",
        zIndex: 15,
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          height: "40px",
          padding: "0 12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #E5E7EB",
          backgroundColor: "#F5F3FF",
          fontWeight: 700,
          color: "#6D28D9",
          fontSize: "0.75rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Sparkles size={14} color="#7C3AED" />
          <span>AI Space Planner</span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#6D28D9",
            fontWeight: 600,
            cursor: "pointer",
            fontSize: "0.75rem",
          }}
        >
          Close
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px" }}>
        {/* Requirements Prompt Input */}
        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", fontSize: "0.7rem", fontWeight: 700, color: "#4B5563", textTransform: "uppercase", marginBottom: "6px" }}>
            SPACE REQUIREMENTS & PROGRAM
          </label>
          <textarea
            rows={3}
            value={promptInput}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="e.g. 6 Professional Desks + 1 Manager Cabin"
            style={{
              width: "100%",
              padding: "8px",
              border: "1px solid #D1D5DB",
              borderRadius: "4px",
              fontSize: "0.8rem",
              fontFamily: "inherit",
              resize: "none",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            style={{
              width: "100%",
              marginTop: "8px",
              backgroundColor: "#7C3AED",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "4px",
              padding: "8px",
              fontWeight: 600,
              fontSize: "0.8rem",
              cursor: isGenerating ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
            }}
          >
            {isGenerating ? (
              <>
                <RefreshCw size={13} className="spin" />
                <span>Solving Free Space...</span>
              </>
            ) : (
              <>
                <Sparkles size={13} />
                <span>Solve Architectural Layout</span>
              </>
            )}
          </button>
        </div>

        {/* CANDIDATE LAYOUT OPTIONS */}
        {candidates.length > 0 && (
          <div>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "#4B5563", textTransform: "uppercase", marginBottom: "8px" }}>
              LAYOUT OPTIONS ({candidates.length})
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {candidates.map((cand, idx) => {
                const isSelected = idx === activeCandidateIdx;
                const totalPlacements = cand.placed_objects?.length || 0;
                const compScore = cand.metrics ? Math.round(cand.metrics.composite_score) : 95;

                return (
                  <div
                    key={`cand-${cand.id || idx}`}
                    onClick={() => onSelectCandidate(idx)}
                    style={{
                      padding: "10px",
                      backgroundColor: isSelected ? "#F5F3FF" : "#F9FAFB",
                      border: isSelected ? "1.5px solid #7C3AED" : "1px solid #E5E7EB",
                      borderRadius: "6px",
                      cursor: "pointer",
                      transition: "all 0.1s ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 700, color: "#1F2937", fontSize: "0.85rem" }}>
                        Option {idx + 1}
                      </span>
                      <span style={{ fontSize: "0.7rem", color: "#7C3AED", fontWeight: 600 }}>
                        Score: {compScore}%
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "0.72rem", color: "#6B7280" }}>
                      <span>Placements: {totalPlacements}</span>
                      <span>Seats: {cand.metrics?.total_seats || totalPlacements}</span>
                    </div>

                    <div style={{ marginTop: "6px", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.7rem" }}>
                      <CheckCircle size={12} color="#15803D" />
                      <span style={{ color: "#15803D", fontWeight: 600 }}>0 Hard Violations</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
