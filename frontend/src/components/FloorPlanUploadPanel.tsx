import React, { useState, useRef, useEffect } from "react";
import {
  uploadFloorPlanFile,
  listProjects,
  createProject,
  ProjectItem,
  IngestionStatusResponse,
} from "../api/ingestion";

interface FloorPlanUploadPanelProps {
  onUploadSuccess: (res: IngestionStatusResponse) => void;
  onSelectExistingFloorPlan?: (projectId: string, floorPlanId: string) => void;
}

const ALLOWED_EXTENSIONS = [".ifc", ".dxf"];
const MAX_FILE_SIZE_MB = 50;

export const FloorPlanUploadPanel: React.FC<FloorPlanUploadPanelProps> = ({
  onUploadSuccess,
  onSelectExistingFloorPlan,
}) => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("proj_101");
  const [newProjectName, setNewProjectName] = useState<string>("");
  const [isCreatingProject, setIsCreatingProject] = useState<boolean>(false);

  const [floorPlanName, setFloorPlanName] = useState<string>("Level 4 Office Area");
  const [floorNumber, setFloorNumber] = useState<number>(4);
  const [buildingName, setBuildingName] = useState<string>("Executive Tower");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [uploadState, setUploadState] = useState<"IDLE" | "UPLOADING" | "INGESTING" | "SUCCESS" | "ERROR">("IDLE");
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [ingestionResult, setIngestionResult] = useState<IngestionStatusResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadProjectsList();
  }, []);

  const loadProjectsList = async () => {
    try {
      const list = await listProjects();
      setProjects(list);
      if (list.length > 0 && !selectedProjectId) {
        setSelectedProjectId(list[0].id);
      }
    } catch (err) {
      console.warn("Using default project fallback list:", err);
      setProjects([
        { id: "proj_101", name: "Enterprise Headquarters Redesign", client_name: "Acme Corp", floor_plans_count: 1 },
      ]);
    }
  };

  const handleCreateNewProject = async () => {
    if (!newProjectName.trim()) return;
    try {
      const created = await createProject(newProjectName.trim(), "Client Corp");
      setProjects((prev) => [...prev, created]);
      setSelectedProjectId(created.id);
      setNewProjectName("");
      setIsCreatingProject(false);
    } catch (err: any) {
      alert(`Failed to create project: ${err.message}`);
    }
  };

  const validateFile = (file: File): boolean => {
    setValidationError(null);
    const ext = "." + file.name.split(".").pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setValidationError(`Unsupported file extension '${ext}'. Please select an .ifc or .dxf file.`);
      return false;
    }

    if (file.size === 0) {
      setValidationError("Selected file is empty (0 bytes).");
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
      if (!floorPlanName || floorPlanName === "Level 4 Office Area") {
        const baseName = file.name.replace(/\.[^/.]+$/, "");
        setFloorPlanName(baseName.replace(/_/g, " "));
      }
    } else {
      setSelectedFile(null);
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
      const file = e.dataTransfer.files[0];
      handleFileSelect(file);
    }
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) {
      setValidationError("Please select or drop an IFC or DXF floor plan file first.");
      return;
    }

    setUploadState("UPLOADING");
    setProgressPercent(0);
    setErrorMessage(null);

    try {
      const result = await uploadFloorPlanFile(
        {
          projectId: selectedProjectId,
          file: selectedFile,
          floorPlanName,
          floorNumber,
          buildingName,
        },
        (pct) => {
          setProgressPercent(pct);
          if (pct >= 100) {
            setUploadState("INGESTING");
          }
        }
      );

      setUploadState("SUCCESS");
      setIngestionResult(result);
      onUploadSuccess(result);
    } catch (err: any) {
      setUploadState("ERROR");
      setErrorMessage(err.message || "An error occurred during file upload or BIM ingestion.");
    }
  };

  return (
    <div
      style={{
        backgroundColor: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: "12px",
        padding: "24px",
        maxWidth: "760px",
        margin: "0 auto",
        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        color: "#f8fafc",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.375rem", fontWeight: 700, color: "#f8fafc" }}>
            Upload Floor Plan Baseline
          </h2>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
            Ingest architectural Revit IFC or 2D CAD DXF drawings into canonical geometry.
          </p>
        </div>
        <span
          style={{
            backgroundColor: "#0284c7",
            color: "#ffffff",
            padding: "4px 10px",
            borderRadius: "9999px",
            fontSize: "0.75rem",
            fontWeight: 700,
          }}
        >
          Task 2.5 Active Entry
        </span>
      </div>

      {/* Metadata Configuration Section */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "20px" }}>
        <div>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: "6px" }}>
            PROJECT
          </label>
          {!isCreatingProject ? (
            <div style={{ display: "flex", gap: "8px" }}>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                style={{
                  flex: 1,
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#f8fafc",
                  borderRadius: "6px",
                  padding: "8px 12px",
                  fontSize: "0.875rem",
                }}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.id})
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setIsCreatingProject(true)}
                style={{
                  backgroundColor: "#334155",
                  color: "#38bdf8",
                  border: "1px solid #475569",
                  borderRadius: "6px",
                  padding: "0 12px",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                + New
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                placeholder="Project Name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                style={{
                  flex: 1,
                  backgroundColor: "#1e293b",
                  border: "1px solid #0284c7",
                  color: "#f8fafc",
                  borderRadius: "6px",
                  padding: "8px 12px",
                  fontSize: "0.875rem",
                }}
              />
              <button
                type="button"
                onClick={handleCreateNewProject}
                style={{
                  backgroundColor: "#0284c7",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  padding: "0 12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => setIsCreatingProject(false)}
                style={{
                  backgroundColor: "#334155",
                  color: "#94a3b8",
                  border: "none",
                  borderRadius: "6px",
                  padding: "0 8px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: "6px" }}>
            FLOOR PLAN NAME
          </label>
          <input
            type="text"
            value={floorPlanName}
            onChange={(e) => setFloorPlanName(e.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#f8fafc",
              borderRadius: "6px",
              padding: "8px 12px",
              fontSize: "0.875rem",
            }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: "6px" }}>
            FLOOR NUMBER
          </label>
          <input
            type="number"
            value={floorNumber}
            onChange={(e) => setFloorNumber(parseInt(e.target.value, 10) || 1)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#f8fafc",
              borderRadius: "6px",
              padding: "8px 12px",
              fontSize: "0.875rem",
            }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: "6px" }}>
            BUILDING / TOWER NAME
          </label>
          <input
            type="text"
            value={buildingName}
            onChange={(e) => setBuildingName(e.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#f8fafc",
              borderRadius: "6px",
              padding: "8px 12px",
              fontSize: "0.875rem",
            }}
          />
        </div>
      </div>

      {/* Drag & Drop File Container */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: isDragging ? "2px dashed #38bdf8" : selectedFile ? "2px solid #0284c7" : "2px dashed #334155",
          backgroundColor: isDragging ? "rgba(56, 189, 248, 0.08)" : selectedFile ? "rgba(2, 132, 199, 0.08)" : "#020617",
          borderRadius: "8px",
          padding: "32px 20px",
          textAlign: "center",
          cursor: "pointer",
          transition: "all 0.2s ease",
          marginBottom: "20px",
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

        <div style={{ fontSize: "2rem", marginBottom: "8px" }}>
          {selectedFile ? "📄" : "📁"}
        </div>

        {selectedFile ? (
          <div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#38bdf8" }}>
              {selectedFile.name}
            </div>
            <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginTop: "4px" }}>
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for Upload & Ingestion
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "4px" }}>
              Drag & drop your architectural floor plan here, or <span style={{ color: "#38bdf8", textDecoration: "underline" }}>browse files</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
              Supported Formats: <strong style={{ color: "#38bdf8" }}>IFC</strong> (.ifc) or <strong style={{ color: "#38bdf8" }}>DXF</strong> (.dxf) up to {MAX_FILE_SIZE_MB}MB
            </div>
          </div>
        )}
      </div>

      {validationError && (
        <div style={{ backgroundColor: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", borderRadius: "6px", padding: "10px 14px", marginBottom: "16px", color: "#fca5a5", fontSize: "0.875rem" }}>
          ⚠️ {validationError}
        </div>
      )}

      {/* Upload & Ingestion Progress Indicators */}
      {uploadState === "UPLOADING" && (
        <div style={{ marginBottom: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.875rem", color: "#38bdf8", marginBottom: "6px" }}>
            <span>Uploading {selectedFile?.name}...</span>
            <span>{progressPercent}%</span>
          </div>
          <div style={{ height: "8px", backgroundColor: "#1e293b", borderRadius: "4px", overflow: "hidden" }}>
            <div
              style={{
                width: `${progressPercent}%`,
                height: "100%",
                backgroundColor: "#0284c7",
                transition: "width 0.2s ease",
              }}
            />
          </div>
        </div>
      )}

      {uploadState === "INGESTING" && (
        <div style={{ backgroundColor: "rgba(14, 165, 233, 0.15)", border: "1px solid #0284c7", borderRadius: "6px", padding: "12px 16px", marginBottom: "20px", color: "#38bdf8", fontSize: "0.875rem", display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ border: "2px solid #0284c7", borderTop: "2px solid transparent", borderRadius: "50%", width: "16px", height: "16px", animation: "spin 1s linear infinite" }} />
          <span>Ingesting BIM geometry with IfcOpenShell / DXF parser... Calculating canonical boundaries.</span>
        </div>
      )}

      {uploadState === "ERROR" && (
        <div style={{ backgroundColor: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", borderRadius: "6px", padding: "14px", marginBottom: "20px", color: "#fca5a5" }}>
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>Upload & Ingestion Error</div>
          <div style={{ fontSize: "0.875rem" }}>{errorMessage}</div>
        </div>
      )}

      {uploadState === "SUCCESS" && ingestionResult && (
        <div style={{ backgroundColor: "rgba(34, 197, 94, 0.1)", border: "1px solid #22c55e", borderRadius: "6px", padding: "16px", marginBottom: "20px", color: "#86efac" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <strong style={{ fontSize: "1rem" }}>Ingestion Complete — PENDING_VERIFICATION</strong>
            <span style={{ fontSize: "0.75rem", backgroundColor: "#15803d", color: "#ffffff", padding: "2px 8px", borderRadius: "4px" }}>
              Version {ingestionResult.version_no}
            </span>
          </div>
          <p style={{ margin: "0 0 12px 0", fontSize: "0.875rem", color: "#cbd5e1" }}>
            File <strong>{ingestionResult.file_name}</strong> successfully parsed and stored. Ready for Layouts Team review.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", fontSize: "0.75rem", backgroundColor: "#020617", padding: "10px", borderRadius: "4px" }}>
            <div>
              <span style={{ color: "#94a3b8" }}>Walls:</span>{" "}
              <strong>{ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "WALL").length || 0}</strong>
            </div>
            <div>
              <span style={{ color: "#94a3b8" }}>Doors:</span>{" "}
              <strong>{ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "DOOR").length || 0}</strong>
            </div>
            <div>
              <span style={{ color: "#94a3b8" }}>Windows:</span>{" "}
              <strong>{ingestionResult.verification_report?.all_elements_geometry?.filter((e) => e.category === "WINDOW").length || 0}</strong>
            </div>
            <div>
              <span style={{ color: "#94a3b8" }}>Net Area:</span>{" "}
              <strong>{ingestionResult.verification_report?.total_net_area_sqm || 0} m²</strong>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Action Bar */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
        {selectedFile && uploadState !== "UPLOADING" && uploadState !== "INGESTING" && (
          <button
            type="button"
            onClick={() => {
              setSelectedFile(null);
              setUploadState("IDLE");
              setIngestionResult(null);
            }}
            style={{
              backgroundColor: "#1e293b",
              color: "#94a3b8",
              border: "1px solid #334155",
              borderRadius: "6px",
              padding: "10px 18px",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Clear Selection
          </button>
        )}

        <button
          type="button"
          onClick={handleUploadSubmit}
          disabled={!selectedFile || uploadState === "UPLOADING" || uploadState === "INGESTING"}
          style={{
            backgroundColor: !selectedFile || uploadState === "UPLOADING" || uploadState === "INGESTING" ? "#334155" : "#0284c7",
            color: !selectedFile || uploadState === "UPLOADING" || uploadState === "INGESTING" ? "#64748b" : "#ffffff",
            border: "none",
            borderRadius: "6px",
            padding: "10px 24px",
            fontSize: "0.875rem",
            fontWeight: 700,
            cursor: !selectedFile || uploadState === "UPLOADING" || uploadState === "INGESTING" ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {uploadState === "UPLOADING" ? "Uploading..." : uploadState === "INGESTING" ? "Ingesting..." : "Upload & Ingest Floor Plan"}
        </button>
      </div>
    </div>
  );
};
