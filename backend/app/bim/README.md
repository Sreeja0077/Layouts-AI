# BIM & Floor-Plan Ingestion Module

## 📌 Purpose & Overview
Parses Revit IFC files, 2D DXF CAD drawings, and raster PDF/images into canonical spatial representations, and reconciles ingested geometry for human verification.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/bim`
- **System Authority:** Ingests raw client architectural assets and extracts structural boundaries (`IfcWall`, `IfcDoor`, `IfcSpace`, 2D CAD Polylines) required by PostGIS and Shapely geometry optimization engines.

## 📁 Files & Responsibilities
- [`ifc_ingest.py`](file:///d:/Layouts%20AI/backend/app/bim/ifc_ingest.py): Revit IFC floor plan geometry parser (`IFCIngestor`, `IFCParsedFloorPlan`, `ExtractedElement`).
  - **Why needed:** Extracts 3D/2D structural elements, GlobalIds, and footprint polygons from uploaded Revit architectural models.
- [`dxf_ingest.py`](file:///d:/Layouts%20AI/backend/app/bim/dxf_ingest.py): 2D AutoCAD DXF CAD drawing parser (`DXFIngestor`, `DXFParsedFloorPlan`, `DXFEntity`).
  - **Why needed:** Provides fallback 2D vector CAD parsing (`LWPOLYLINE`, `LINE`, `ARC`) and layer classification when 3D BIM models are unavailable.
- [`reconciliation.py`](file:///d:/Layouts%20AI/backend/app/bim/reconciliation.py): Floor plan geometry verification and anomaly report engine (`GeometryReconciler`, `GeometryVerificationReport`, `GeometryAnomalyWarning`).
  - **Why needed:** Validates room boundaries, detects unclosed wall polylines or missing doors, and generates verification reports for Layouts Team review prior to layout optimization.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
