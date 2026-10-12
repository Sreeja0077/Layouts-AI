/**
 * Professional AI Space Planner Side Panel for Layouts AI Workstation.
 * Phase 8.5: Natural Language Requirement Analysis, Semantic Normalization & Interactive Clarification.
 */

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  HelpCircle,
  Send,
  Layers,
  MapPin,
  Users,
  Compass,
} from "lucide-react";
import { RequirementAnalysisResponse } from "../../api/requirements";
import { LayoutSuggestionPayload } from "../../api/layout";

export interface AILayoutPanelProps {
  promptInput: string;
  onPromptChange: (val: string) => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
  analysisResult: RequirementAnalysisResponse | null;
  error: string | null;
  onClarify: (questionId: string, answer: string) => void;
  isClarifying: boolean;
  candidates?: LayoutSuggestionPayload[];
  activeCandidateIdx?: number;
  onSelectCandidate?: (idx: number) => void;
  onClose: () => void;
}

export const AILayoutPanel: React.FC<AILayoutPanelProps> = ({
  promptInput,
  onPromptChange,
  onAnalyze,
  isAnalyzing,
  analysisResult,
  error,
  onClarify,
  isClarifying,
  candidates = [],
  activeCandidateIdx = 0,
  onSelectCandidate,
  onClose,
}) => {
  // Local state for question answers
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const handleAnswerChange = (questionId: string, val: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: val }));
  };

  const handleOptionClick = (questionId: string, opt: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: opt }));
    onClarify(questionId, opt);
  };

  const handleAnswerSubmit = (questionId: string) => {
    const val = answers[questionId]?.trim();
    if (!val) return;
    onClarify(questionId, val);
  };

  return (
    <aside
      id="ai-layout-panel"
      style={{
        width: "360px",
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
          height: "44px",
          padding: "0 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #E5E7EB",
          backgroundColor: "#F5F3FF",
          fontWeight: 700,
          color: "#6D28D9",
          fontSize: "0.8rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Sparkles size={16} color="#7C3AED" />
          <span>AI Space Planner</span>
        </div>
        <button
          onClick={onClose}
          id="close-ai-panel-btn"
          style={{
            background: "none",
            border: "none",
            color: "#6D28D9",
            fontWeight: 600,
            cursor: "pointer",
            fontSize: "0.75rem",
            padding: "4px 8px",
            borderRadius: "4px",
          }}
        >
          Close
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "14px" }}>
        {/* Requirements Prompt Input */}
        <div style={{ marginBottom: "16px" }}>
          <label
            style={{
              display: "block",
              fontSize: "0.7rem",
              fontWeight: 700,
              color: "#4B5563",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "6px",
            }}
          >
            Space Requirements & Program
          </label>
          <textarea
            id="requirement-input-textarea"
            rows={3}
            value={promptInput}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="e.g. 6 Professional Desks + 1 Manager Cabin near the window"
            disabled={isAnalyzing || isClarifying}
            style={{
              width: "100%",
              padding: "10px",
              border: "1px solid #D1D5DB",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontFamily: "inherit",
              resize: "none",
              outline: "none",
              boxSizing: "border-box",
              lineHeight: 1.4,
              backgroundColor: isAnalyzing ? "#F9FAFB" : "#FFFFFF",
            }}
          />
          <button
            id="analyze-requirement-btn"
            onClick={onAnalyze}
            disabled={isAnalyzing || isClarifying || !promptInput.trim()}
            style={{
              width: "100%",
              marginTop: "8px",
              backgroundColor: isAnalyzing || !promptInput.trim() ? "#A78BFA" : "#7C3AED",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "6px",
              padding: "9px 12px",
              fontWeight: 600,
              fontSize: "0.82rem",
              cursor: isAnalyzing || !promptInput.trim() ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              transition: "background-color 0.15s ease",
            }}
          >
            {isAnalyzing ? (
              <>
                <RefreshCw size={14} className="spin" />
                <span>Analyzing Requirement...</span>
              </>
            ) : (
              <>
                <Sparkles size={14} />
                <span>Analyze Requirement</span>
              </>
            )}
          </button>
        </div>

        {/* Backend Error Banner */}
        {error && (
          <div
            id="ai-error-banner"
            style={{
              marginBottom: "16px",
              padding: "10px 12px",
              backgroundColor: "#FEF2F2",
              border: "1px solid #FCA5A5",
              borderRadius: "6px",
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
              color: "#991B1B",
              fontSize: "0.76rem",
              lineHeight: 1.4,
            }}
          >
            <AlertCircle size={15} style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <div style={{ fontWeight: 700, marginBottom: "2px" }}>Analysis Error</div>
              <div>{error}</div>
            </div>
          </div>
        )}

        {/* CLARIFICATION QUESTIONS SECTION */}
        {analysisResult?.needs_clarification && analysisResult.questions.length > 0 && (
          <div id="clarification-section" style={{ marginBottom: "16px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 10px",
                backgroundColor: "#FFFBEB",
                border: "1px solid #FDE68A",
                borderRadius: "6px",
                color: "#92400E",
                fontSize: "0.75rem",
                fontWeight: 600,
                marginBottom: "10px",
              }}
            >
              <HelpCircle size={15} color="#D97706" />
              <span>Clarification Required ({analysisResult.questions.length})</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {analysisResult.questions.map((q) => {
                const currentAnswer = answers[q.question_id] || "";
                return (
                  <div
                    key={q.question_id}
                    id={`question-card-${q.question_id}`}
                    style={{
                      padding: "12px",
                      backgroundColor: "#F9FAFB",
                      border: "1px solid #E5E7EB",
                      borderRadius: "6px",
                    }}
                  >
                    <div
                      style={{
                        fontWeight: 600,
                        color: "#1F2937",
                        fontSize: "0.8rem",
                        marginBottom: "8px",
                        lineHeight: 1.35,
                      }}
                    >
                      {q.question_text}
                    </div>

                    {/* Suggested Options Chips (if available) */}
                    {q.suggested_options && q.suggested_options.length > 0 && (
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "6px",
                          marginBottom: "8px",
                        }}
                      >
                        {q.suggested_options.map((opt) => (
                          <button
                            key={opt}
                            disabled={isClarifying}
                            onClick={() => handleOptionClick(q.question_id, opt)}
                            style={{
                              padding: "4px 8px",
                              backgroundColor: "#EDE9FE",
                              color: "#6D28D9",
                              border: "1px solid #DDD6FE",
                              borderRadius: "4px",
                              fontSize: "0.72rem",
                              fontWeight: 600,
                              cursor: isClarifying ? "not-allowed" : "pointer",
                              transition: "all 0.1s ease",
                            }}
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Free-text input + submit */}
                    <div style={{ display: "flex", gap: "6px" }}>
                      <input
                        type="text"
                        value={currentAnswer}
                        onChange={(e) => handleAnswerChange(q.question_id, e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleAnswerSubmit(q.question_id);
                        }}
                        placeholder="Type answer..."
                        disabled={isClarifying}
                        style={{
                          flex: 1,
                          padding: "6px 8px",
                          border: "1px solid #D1D5DB",
                          borderRadius: "4px",
                          fontSize: "0.78rem",
                          outline: "none",
                        }}
                      />
                      <button
                        onClick={() => handleAnswerSubmit(q.question_id)}
                        disabled={isClarifying || !currentAnswer.trim()}
                        style={{
                          backgroundColor: "#7C3AED",
                          color: "#FFFFFF",
                          border: "none",
                          borderRadius: "4px",
                          padding: "0 10px",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          cursor: isClarifying || !currentAnswer.trim() ? "not-allowed" : "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {isClarifying ? (
                          <RefreshCw size={11} className="spin" />
                        ) : (
                          <Send size={11} />
                        )}
                        <span>Submit</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* NORMALIZED REQUIREMENT RESULT (When complete & needs_clarification=false) */}
        {analysisResult && !analysisResult.needs_clarification && (
          <div id="normalized-requirement-card" style={{ marginBottom: "16px" }}>
            <div
              style={{
                padding: "10px 12px",
                backgroundColor: "#F0FDF4",
                border: "1px solid #BBF7D0",
                borderRadius: "6px",
                marginBottom: "12px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "4px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <CheckCircle size={15} color="#16A34A" />
                  <span style={{ fontWeight: 700, color: "#166534", fontSize: "0.8rem" }}>
                    Requirement Understood
                  </span>
                </div>
                <span
                  style={{
                    backgroundColor: "#DCFCE7",
                    color: "#15803D",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    fontSize: "0.7rem",
                    fontWeight: 700,
                  }}
                >
                  {(analysisResult.confidence * 100).toFixed(0)}% Conf
                </span>
              </div>
              <div style={{ color: "#166534", fontSize: "0.74rem", lineHeight: 1.35 }}>
                {analysisResult.reasoning}
              </div>
            </div>

            {/* Program Items */}
            <div style={{ marginBottom: "12px" }}>
              <div
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  color: "#4B5563",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  marginBottom: "6px",
                }}
              >
                Requested Elements ({analysisResult.requirement_set.items.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {analysisResult.requirement_set.items.map((item, idx) => (
                  <div
                    key={item.id || idx}
                    style={{
                      padding: "8px 10px",
                      backgroundColor: "#F9FAFB",
                      border: "1px solid #E5E7EB",
                      borderRadius: "6px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, color: "#1F2937", fontSize: "0.78rem" }}>
                        {item.quantity > 0 ? `${item.quantity} × ` : ""}
                        {item.semantic_type?.replace(/_/g, " ") || item.raw_phrase}
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "#6B7280" }}>
                        Phrase: "{item.raw_phrase}"
                      </div>
                    </div>
                    {item.dimensions_override && (
                      <span
                        style={{
                          fontSize: "0.68rem",
                          backgroundColor: "#F3F4F6",
                          color: "#374151",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        Dimensions Defined
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Spatial Preferences */}
            {analysisResult.requirement_set.preferences.length > 0 && (
              <div style={{ marginBottom: "12px" }}>
                <div
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 700,
                    color: "#4B5563",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    marginBottom: "6px",
                  }}
                >
                  Spatial Preferences
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  {analysisResult.requirement_set.preferences.map((p, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "6px 8px",
                        backgroundColor: "#F5F3FF",
                        border: "1px solid #EDE9FE",
                        borderRadius: "4px",
                        fontSize: "0.73rem",
                        color: "#5B21B6",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <Compass size={13} color="#7C3AED" />
                      <span>
                        {p.preference_type.replace(/_/g, " ")} ({p.target_zone}) • {p.importance}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Target Density & Context */}
            <div
              style={{
                padding: "8px 10px",
                backgroundColor: "#F9FAFB",
                border: "1px solid #E5E7EB",
                borderRadius: "6px",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
                fontSize: "0.72rem",
                color: "#4B5563",
              }}
            >
              {analysisResult.requirement_set.target_density_seats && (
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <Users size={13} color="#6B7280" />
                  <span>Target Seats: {analysisResult.requirement_set.target_density_seats}</span>
                </div>
              )}
              {analysisResult.requirement_set.room_id && (
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <MapPin size={13} color="#6B7280" />
                  <span>Region: {analysisResult.requirement_set.room_id}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* CANDIDATE LAYOUT OPTIONS (Only displayed when real candidate models exist) */}
        {candidates.length > 0 && (
          <div>
            <div
              style={{
                fontSize: "0.7rem",
                fontWeight: 700,
                color: "#4B5563",
                textTransform: "uppercase",
                marginBottom: "8px",
              }}
            >
              Layout Options ({candidates.length})
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {candidates.map((cand, idx) => {
                const isSelected = idx === activeCandidateIdx;
                const totalPlacements = cand.placed_objects?.length || 0;
                const compScore = cand.metrics ? Math.round(cand.metrics.composite_score) : null;

                return (
                  <div
                    key={`cand-${cand.id || idx}`}
                    onClick={() => onSelectCandidate && onSelectCandidate(idx)}
                    style={{
                      padding: "10px",
                      backgroundColor: isSelected ? "#F5F3FF" : "#F9FAFB",
                      border: isSelected ? "1.5px solid #7C3AED" : "1px solid #E5E7EB",
                      borderRadius: "6px",
                      cursor: "pointer",
                      transition: "all 0.1s ease",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "4px",
                      }}
                    >
                      <span style={{ fontWeight: 700, color: "#1F2937", fontSize: "0.85rem" }}>
                        Option {idx + 1}
                      </span>
                      {compScore !== null && (
                        <span style={{ fontSize: "0.7rem", color: "#7C3AED", fontWeight: 600 }}>
                          Score: {compScore}%
                        </span>
                      )}
                    </div>

                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        fontSize: "0.72rem",
                        color: "#6B7280",
                      }}
                    >
                      <span>Placements: {totalPlacements}</span>
                      {cand.metrics?.total_seats && <span>Seats: {cand.metrics.total_seats}</span>}
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
