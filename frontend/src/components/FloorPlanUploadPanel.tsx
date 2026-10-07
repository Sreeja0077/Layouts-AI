import React, { useState, useRef, useEffect } from "react";
import {
  uploadFloorPlanFile,
  listProjects,
  listFloorPlans,
  ProjectItem,
  FloorPlanItem,
  IngestionStatusResponse,
} from "../api/ingestion";

interface FloorPlanUploadPanelProps {
  onOpenEditor: (res: IngestionStatusResponse) => void;
  onOpenExistingFloorPlan?: (projectId: string, floorPlanId: string) => void;
}

const ALLOWED_EXTENSIONS = [".ifc", ".dxf"];
const MAX_FILE_SIZE_MB = 1000;

export const FloorPlanUploadPanel: React.FC<FloorPlanUploadPanelProps> = ({
  onOpenEditor,
  onOpenExistingFloorPlan,
}) => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(() => {
    return localStorage.getItem("layouts_ai_active_project_id") || "proj_101";
  });
  const [recentFloorPlans, setRecentFloorPlans] = useState<FloorPlanItem[]>([]);

  const [floorPlanName, setFloorPlanName] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [uploadState, setUploadState] = useState<"IDLE" | "SELECTED" | "UPLOADING" | "INGESTING" | "READY" | "ERROR">("IDLE");
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [ingestionResult, setIngestionResult] = useState<IngestionStatusResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadProjectsAndFloorPlans();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadFloorPlansForProject(selectedProjectId);
    }
  }, [selectedProjectId]);

  const loadProjectsAndFloorPlans = async () => {
    try {
      const list = await listProjects();
      setProjects(list);
      const savedProj = localStorage.getItem("layouts_ai_active_project_id");
      if (savedProj && list.some(p => p.id === savedProj)) {
        setSelectedProjectId(savedProj);
      } else if (list.length > 0) {
        setSelectedProjectId(list[0].id);
      }
    } catch (err) {
      setProjects([{ id: "proj_101", name: "Enterprise Headquarters Redesign", client_name: "Acme Corp" }]);
    }
  };

  const loadFloorPlansForProject = async (projId: string) => {
    try {
      const fps = await listFloorPlans(projId);
      const userFps = fps.filter(fp =>
        !fp.name.toLowerCase().includes("sample_floor_plan") &&
        !fp.name.toLowerCase().includes("test plan") &&
        fp.id !== "fp_501"
      );
      setRecentFloorPlans(userFps);
    } catch (err) {
      setRecentFloorPlans([]);
    }
  };

  const validateFile = (file: File): boolean => {
    setValidationError(null);
    const ext = "." + file.name.split(".").pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setValidationError(`Unsupported file format '${ext}'. Layouts AI accepts IFC (.ifc) or DXF (.dxf) floor plans.`);
      return false;
    }

    if (file.size === 0) {
      setValidationError("The selected file is empty (0 bytes).");
      return false;
    }

    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setValidationError(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum limit of ${MAX_FILE_SIZE_MB}MB.`);
      return false;
    }

    return true;
  };

  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file);
      const baseName = file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
      setFloorPlanName(baseName);
      setUploadState("SELECTED");
    } else {
      setSelectedFile(null);
      setUploadState("IDLE");
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) return;

    setUploadState("UPLOADING");
    setProgressPercent(0);
    setErrorMessage(null);

    try {
      const result = await uploadFloorPlanFile(
        {
          projectId: selectedProjectId,
          file: selectedFile,
          floorPlanName: floorPlanName || selectedFile.name,
        },
        (pct) => {
          setProgressPercent(pct);
          if (pct >= 100) {
            setUploadState("INGESTING");
          }
        }
      );

      setUploadState("READY");
      setIngestionResult(result);
      loadFloorPlansForProject(selectedProjectId);
      // Instantly open uploaded file in 2D Canvas Editor
      onOpenEditor(result);
    } catch (err: any) {
      setUploadState("ERROR");
      setErrorMessage(err.message || "BIM/DXF ingestion failed. Please check file formatting.");
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: "32px", width: "100%", flex: 1, color: "#f8fafc", fontFamily: "sans-serif", boxSizing: "border-box" }}>
      {/* Primary Left Workstation: Drag & Drop + Processing Flow */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {/* Workspace Title & Project Context */}
        <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700, color: "#f8fafc", letterSpacing: "-0.01em" }}>
              Upload Floor Plan
            </h1>
            <p style={{ margin: "6px 0 0 0", fontSize: "0.9375rem", color: "#94a3b8" }}>
              Import architectural IFC or DXF drawings to automatically generate canonical floor plans.
            </p>
          </div>

          <div style={{ minWidth: "260px" }}>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#64748b", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              TARGET PROJECT
            </label>
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              style={{
                width: "100%",
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                color: "#f8fafc",
                borderRadius: "8px",
                padding: "10px 14px",
                fontSize: "0.875rem",
                fontWeight: 600,
              }}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Full-width Drag & Drop Upload Zone (IDLE / SELECTED states) */}
        {(uploadState === "IDLE" || uploadState === "SELECTED") && (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            style={{
              flex: 1,
              minHeight: "360px",
              border: isDragging ? "2px dashed #0284c7" : selectedFile ? "2px solid #0369a1" : "2px dashed #334155",
              backgroundColor: isDragging ? "rgba(2, 132, 199, 0.08)" : selectedFile ? "rgba(15, 23, 42, 0.95)" : "#0f172a",
              borderRadius: "12px",
              padding: "48px 32px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              textAlign: "center",
              transition: "all 0.2s ease-in-out",
              marginBottom: "24px",
              boxSizing: "border-box",
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".ifc,.dxf"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />

            {!selectedFile ? (
              <div style={{ maxWidth: "560px" }}>
                <div style={{ width: "64px", height: "64px", margin: "0 auto 16px auto", borderRadius: "12px", backgroundColor: "#1e293b", display: "flex", alignItems: "center", justifyContent: "center", color: "#38bdf8", fontSize: "2rem", boxShadow: "0 8px 16px -4px rgba(0, 0, 0, 0.4)" }}>
                  📐
                </div>
                <h3 style={{ margin: "0 0 8px 0", fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
                  Drag and drop your architectural file here
                </h3>
                <p style={{ margin: "0 0 24px 0", fontSize: "0.9375rem", color: "#94a3b8", lineHeight: 1.5 }}>
                  Layouts AI automatically validates geometry, extracts structural elements, and prepares your floor plan for interactive layout planning.
                </p>
                <div style={{ display: "flex", justifyContent: "center", gap: "12px", marginBottom: "28px" }}>
                  <span style={{ backgroundColor: "#1e293b", color: "#38bdf8", border: "1px solid #334155", padding: "4px 12px", borderRadius: "6px", fontSize: "0.8125rem", fontWeight: 700 }}>
                    IFC (Revit 3D)
                  </span>
                  <span style={{ backgroundColor: "#1e293b", color: "#38bdf8", border: "1px solid #334155", padding: "4px 12px", borderRadius: "6px", fontSize: "0.8125rem", fontWeight: 700 }}>
                    DXF (2D CAD)
                  </span>
                  <span style={{ color: "#64748b", fontSize: "0.8125rem", alignSelf: "center" }}>
                    Supports large architectural files (up to 1GB)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    backgroundColor: "#0284c7",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "8px",
                    padding: "12px 28px",
                    fontSize: "0.9375rem",
                    fontWeight: 700,
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(2, 132, 199, 0.4)",
                  }}
                >
                  Browse Files
                </button>
              </div>
            ) : (
              <div style={{ width: "100%", maxWidth: "640px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", backgroundColor: "#1e293b", padding: "20px 24px", borderRadius: "10px", border: "1px solid #334155", marginBottom: "24px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <div style={{ width: "48px", height: "48px", borderRadius: "8px", backgroundColor: "#0284c7", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "0.9375rem" }}>
                      {selectedFile.name.split(".").pop()?.toUpperCase()}
                    </div>
                    <div style={{ textAlign: "left" }}>
                      <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#f8fafc" }}>
                        {selectedFile.name}
                      </div>
                      <div style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: "2px" }}>
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for automatic geometry validation
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFile(null);
                      setUploadState("IDLE");
                    }}
                    style={{
                      backgroundColor: "transparent",
                      color: "#94a3b8",
                      border: "none",
                      fontSize: "1.25rem",
                      cursor: "pointer",
                      padding: "4px 8px",
                    }}
                  >
                    ✕
                  </button>
                </div>

                <div style={{ textAlign: "left", marginBottom: "24px" }}>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    FLOOR PLAN NAME
                  </label>
                  <input
                    type="text"
                    value={floorPlanName}
                    onChange={(e) => setFloorPlanName(e.target.value)}
                    placeholder="Floor Plan Name"
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      backgroundColor: "#0f172a",
                      border: "1px solid #334155",
                      color: "#f8fafc",
                      borderRadius: "8px",
                      padding: "12px 16px",
                      fontSize: "0.9375rem",
                    }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "14px" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFile(null);
                      setUploadState("IDLE");
                    }}
                    style={{
                      backgroundColor: "#1e293b",
                      color: "#94a3b8",
                      border: "1px solid #334155",
                      borderRadius: "8px",
                      padding: "12px 20px",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Change File
                  </button>
                  <button
                    type="button"
                    onClick={handleUploadAndProcess}
                    style={{
                      backgroundColor: "#0284c7",
                      color: "#ffffff",
                      border: "none",
                      borderRadius: "8px",
                      padding: "12px 32px",
                      fontSize: "0.9375rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      boxShadow: "0 4px 12px rgba(2, 132, 199, 0.4)",
                    }}
                  >
                    Upload & Process Floor Plan
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {validationError && (
          <div style={{ backgroundColor: "rgba(239, 68, 68, 0.12)", border: "1px solid #ef4444", borderRadius: "8px", padding: "14px 18px", marginBottom: "24px", color: "#fca5a5", fontSize: "0.875rem" }}>
            ⚠️ {validationError}
          </div>
        )}

        {/* Processing State Timeline */}
        {(uploadState === "UPLOADING" || uploadState === "INGESTING") && (
          <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "36px 32px", marginBottom: "24px", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <h3 style={{ margin: "0 0 20px 0", fontSize: "1.25rem", fontWeight: 700, color: "#38bdf8" }}>
              Processing Floor Plan Geometry...
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "28px", fontSize: "0.9375rem" }}>
              <div style={{ color: "#22c55e", display: "flex", alignItems: "center", gap: "10px" }}>
                <span>✓</span> File uploaded ({progressPercent}%)
              </div>
              <div style={{ color: progressPercent >= 100 ? "#22c55e" : "#64748b", display: "flex", alignItems: "center", gap: "10px" }}>
                <span>{progressPercent >= 100 ? "✓" : "•"}</span> Format & syntax verified
              </div>
              <div style={{ color: uploadState === "INGESTING" ? "#38bdf8" : "#64748b", display: "flex", alignItems: "center", gap: "10px" }}>
                <span>{uploadState === "INGESTING" ? "⚙" : "•"}</span> Extracting walls, doors, windows & columns (IfcOpenShell/DXF)
              </div>
              <div style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "10px" }}>
                <span>•</span> Normalizing coordinates to world meters
              </div>
              <div style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "10px" }}>
                <span>•</span> Building canonical floor plan model
              </div>
            </div>

            <div style={{ height: "10px", backgroundColor: "#1e293b", borderRadius: "5px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: "100%",
                  backgroundColor: "#0284c7",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          </div>
        )}

        {/* Error State */}
        {uploadState === "ERROR" && (
          <div style={{ backgroundColor: "rgba(239, 68, 68, 0.12)", border: "1px solid #ef4444", borderRadius: "12px", padding: "28px", marginBottom: "24px" }}>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.25rem", fontWeight: 700, color: "#f87171" }}>
              Unable to Process Floor Plan
            </h3>
            <p style={{ margin: "0 0 20px 0", fontSize: "0.9375rem", color: "#fca5a5", lineHeight: 1.5 }}>
              {errorMessage}
            </p>
            <div style={{ display: "flex", gap: "14px" }}>
              <button
                type="button"
                onClick={() => {
                  setUploadState("IDLE");
                  setSelectedFile(null);
                }}
                style={{
                  backgroundColor: "#ef4444",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "8px",
                  padding: "10px 20px",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Success State (Floor Plan Ready) */}
        {uploadState === "READY" && ingestionResult && (
          <div style={{ backgroundColor: "rgba(15, 23, 42, 0.95)", border: "1px solid #0369a1", borderRadius: "12px", padding: "36px", marginBottom: "24px", flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
                <div>
                  <div style={{ color: "#22c55e", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>
                    ✓ AUTOMATIC VALIDATION PASSED
                  </div>
                  <h2 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc" }}>
                    Floor Plan Ready
                  </h2>
                </div>
                <span style={{ backgroundColor: "#15803d", color: "#ffffff", padding: "6px 14px", borderRadius: "9999px", fontSize: "0.8125rem", fontWeight: 700 }}>
                  READY
                </span>
              </div>

              <p style={{ margin: "0 0 24px 0", fontSize: "0.9375rem", color: "#cbd5e1", lineHeight: 1.5 }}>
                Geometry for <strong>{ingestionResult.file_name}</strong> has been extracted, normalized to world meters, and structured into canonical floor plan entities.
              </p>

              {/* Extracted Element Summary Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "14px", backgroundColor: "#020617", padding: "20px", borderRadius: "10px", border: "1px solid #1e293b", marginBottom: "28px" }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#38bdf8" }}>
                    {ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "WALL").length || 0}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: "2px" }}>Walls</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#38bdf8" }}>
                    {ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "DOOR").length || 0}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: "2px" }}>Doors</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#38bdf8" }}>
                    {ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "WINDOW").length || 0}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: "2px" }}>Windows</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#38bdf8" }}>
                    {ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "COLUMN").length || 0}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: "2px" }}>Columns</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#38bdf8" }}>
                    {ingestionResult.verification_report?.total_net_area_sqm || 0} m²
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: "2px" }}>Net Area</div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "14px" }}>
              <button
                type="button"
                onClick={() => {
                  setUploadState("IDLE");
                  setSelectedFile(null);
                }}
                style={{
                  backgroundColor: "#1e293b",
                  color: "#94a3b8",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  padding: "12px 20px",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Upload Another
              </button>
              <button
                type="button"
                onClick={() => onOpenEditor(ingestionResult)}
                style={{
                  backgroundColor: "#0284c7",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "8px",
                  padding: "14px 32px",
                  fontSize: "0.9375rem",
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: "0 4px 12px rgba(2, 132, 199, 0.4)",
                }}
              >
                Open Floor Plan in 2D Editor →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Secondary Right Column: Recent Project Floor Plans Workspace Sidebar */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "24px", flex: 1 }}>
          <h3 style={{ margin: "0 0 16px 0", fontSize: "1.125rem", fontWeight: 700, color: "#f8fafc", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span>Recent Floor Plans</span>
            <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 400 }}>{recentFloorPlans.length} plans</span>
          </h3>

          {recentFloorPlans.length === 0 ? (
            <div style={{ color: "#64748b", fontSize: "0.875rem", textAlign: "center", padding: "36px 12px" }}>
              No floor plans ingested for this project yet. Upload an IFC or DXF file to get started.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {recentFloorPlans.map((fp) => (
                <div
                  key={fp.id}
                  style={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    padding: "14px 16px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#f8fafc" }}>
                      {fp.name}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px", display: "flex", gap: "8px" }}>
                      <span>Floor {fp.floor_number || 1}</span>
                      <span>•</span>
                      <span style={{ color: "#22c55e", fontWeight: 700 }}>READY</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      if (onOpenExistingFloorPlan) {
                        onOpenExistingFloorPlan(selectedProjectId, fp.id);
                      }
                    }}
                    style={{
                      backgroundColor: "#0284c7",
                      color: "#ffffff",
                      border: "none",
                      borderRadius: "6px",
                      padding: "8px 14px",
                      fontSize: "0.8125rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Open
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
