# BIM & Floor-Plan Ingestion Module

## 📌 Purpose & Overview
Parses Revit IFC files (`.ifc`), 2D DXF CAD drawings (`.dxf`), and raster assets into canonical spatial representations, and reconciles ingested geometry for human verification.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/bim`
- **System Authority:** Ingests raw client architectural assets and extracts structural boundaries (`IfcWall`, `IfcDoor`, `IfcWindow`, `IfcColumn`, `IfcSpace`, 2D CAD Polylines) required by PostGIS and Shapely geometry optimization engines.

## 📁 Files & Responsibilities
- [`ifc_ingest.py`](file:///d:/Layouts%20AI/backend/app/bim/ifc_ingest.py): Authoritative Revit IFC floor plan geometry parser (`IFCIngestor`, `IFCParsedFloorPlan`, `ExtractedElement`, `GeometryStatus`, `GeometryType`).
  - **Parser Engine:** Uses `IfcOpenShell` as the authoritative IFC parsing engine.
  - **Interchange Format:** IFC (ISO-10303-21 STEP) is the canonical parseable interchange format for Revit exports. Direct native `.rvt` parsing is not implemented.
  - **2D Mesh Face Projection:** Projects actual 3D triangulated mesh faces from `ifcopenshell.geom.create_shape()` onto the 2D XY plane, filters degenerate zero-area faces, and unions projected face geometry deterministically using Shapely (`unary_union`).
  - **Concavity & Topology Preservation:** Preserves concavities, interior rings (holes), and `MultiPolygon` topologies (`Polygon` or `MultiPolygon`). Primary footprint is never reduced to a convex hull or bounding box.
  - **Zero-Fabricated Geometry Policy:** No fake bounding boxes, placement-based synthetic dimensions, or invented coordinates exist. Failed shape extractions return empty boundary arrays (`boundary_vertices = []`, `geometry_type = None`, `geometry_coordinates = None`) with `geometry_status = GeometryStatus.FAILED` and machine-readable `geometry_error` details.
  - **GlobalId Preservation:** Preserves original IFC `GlobalId` (`ifc_global_id` and `global_id`) on all elements for stable cross-export reconciliation.
  - **Unit Normalization:** Detects project length unit declarations (`FOOT`, `MILLI`, `METRE`) via `ifcopenshell.util.unit.calculate_unit_scale` and normalizes all 2D coordinates into meters (`m`) with scale metadata.
  - **Provenance & Reference Metadata:** Captures schema, file timestamp, exporting application, project/building names, map conversion (`IfcMapConversion`), and projected CRS (`IfcProjectedCRS`) metadata when available.
  - **Error Handling:** Raises explicit `FileNotFoundError`, `ImportError`, and `ValueError` exceptions without silent exception swallowing or mock fallbacks in production.
- [`dxf_ingest.py`](file:///d:/Layouts%20AI/backend/app/bim/dxf_ingest.py): 2D AutoCAD DXF CAD drawing parser (`DXFIngestor`, `DXFParsedFloorPlan`, `DXFEntity`).
- [`reconciliation.py`](file:///d:/Layouts%20AI/backend/app/bim/reconciliation.py): Floor plan geometry verification and anomaly report engine (`GeometryReconciler`).

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic v2 / JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*

