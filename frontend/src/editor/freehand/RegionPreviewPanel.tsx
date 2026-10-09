/**
 * Region Preview Information Panel Component (Task 6.2).
 * Displays live area (m²), perimeter (m), centroid (m), vertex count, and preview status.
 */

import React from "react";
import { RegionPreview } from "./freehandTypes";

interface RegionPreviewPanelProps {
  regionPreview: RegionPreview | null;
  onClear?: () => void;
}

export const RegionPreviewPanel: React.FC<RegionPreviewPanelProps> = ({
  regionPreview,
  onClear,
}) => {
  if (!regionPreview || !regionPreview.isClosed) return null;

  const serverVal = regionPreview.serverValidation;

  return (
    <div
      style={{
        position: "absolute",
        top: "16px",
        right: "16px",
        width: "280px",
        backgroundColor: "rgba(30, 41, 59, 0.95)",
        backdropFilter: "blur(4px)",
        border: "1px solid #475569",
        borderRadius: "8px",
        padding: "12px 16px",
        color: "#f8fafc",
        fontSize: "0.8125rem",
        zIndex: 20,
        boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.3)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <span style={{ color: "#c084fc", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "0.75rem" }}>
          Selected Region
        </span>
        {serverVal ? (
          <span
            style={{
              fontSize: "0.7rem",
              backgroundColor: serverVal.isValid
                ? serverVal.isClipped
                  ? "rgba(56, 189, 248, 0.2)"
                  : "rgba(34, 197, 94, 0.2)"
                : "rgba(239, 68, 68, 0.2)",
              color: serverVal.isValid
                ? serverVal.isClipped
                  ? "#38bdf8"
                  : "#4ade80"
                : "#f87171",
              padding: "2px 6px",
              borderRadius: "4px",
              border: `1px solid ${
                serverVal.isValid
                  ? serverVal.isClipped
                    ? "rgba(56, 189, 248, 0.4)"
                    : "rgba(34, 197, 94, 0.4)"
                  : "rgba(239, 68, 68, 0.4)"
              }`,
              fontWeight: 600,
            }}
          >
            {serverVal.isValid
              ? serverVal.isClipped
                ? "Authoritative (Clipped)"
                : "Authoritative (Enclosed)"
              : "No Overlap"}
          </span>
        ) : (
          <span style={{ fontSize: "0.7rem", backgroundColor: "rgba(168, 85, 247, 0.2)", color: "#e9d5ff", padding: "2px 6px", borderRadius: "4px", border: "1px solid rgba(168, 85, 247, 0.4)" }}>
            Preview (Unvalidated)
          </span>
        )}
      </div>

      {serverVal && !serverVal.isValid ? (
        <div style={{ color: "#f87171", fontSize: "0.75rem", marginBottom: "6px" }}>
          ⚠️ {serverVal.message}
        </div>
      ) : regionPreview.isValid ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#94a3b8" }}>
              {serverVal ? "Authoritative Area:" : "Area:"}
            </span>
            <span style={{ color: "#38bdf8", fontWeight: 700 }}>
              {(serverVal ? serverVal.areaSqMeters : regionPreview.areaSqMeters).toFixed(2)} m²
            </span>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#94a3b8" }}>Perimeter:</span>
            <span style={{ color: "#f8fafc", fontWeight: 600 }}>
              {(serverVal ? serverVal.perimeterMeters : regionPreview.perimeterMeters).toFixed(2)} m
            </span>
          </div>

          {(serverVal ? serverVal.centroid : regionPreview.centroid) && (
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#94a3b8" }}>Centroid:</span>
              <span style={{ color: "#f8fafc", fontWeight: 600 }}>
                ({(serverVal ? serverVal.centroid! : regionPreview.centroid!).x.toFixed(2)}m, {(serverVal ? serverVal.centroid! : regionPreview.centroid!).y.toFixed(2)}m)
              </span>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#94a3b8" }}>Vertices:</span>
            <span style={{ color: "#cbd5e1" }}>
              {(serverVal ? serverVal.clippedWorldPoints : regionPreview.worldPoints).length} points
            </span>
          </div>

          {serverVal?.isClipped && (
            <div style={{ color: "#38bdf8", fontSize: "0.7rem", marginTop: "2px" }}>
              ✂️ Clipped against room boundary
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: "#fbbf24", fontSize: "0.75rem" }}>
          ⚠️ Region too small to calculate. Please draw a larger closed area.
        </div>
      )}

      {onClear && (
        <button
          onClick={onClear}
          style={{
            marginTop: "10px",
            width: "100%",
            backgroundColor: "transparent",
            color: "#f87171",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            borderRadius: "4px",
            padding: "6px 8px",
            fontSize: "0.75rem",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          Clear Region
        </button>
      )}
    </div>
  );
};


