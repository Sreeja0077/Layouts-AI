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
- [`dxf_ingest.py`](file:///d:/Layouts%20AI/backend/app/bim/dxf_ingest.py): Authoritative 2D AutoCAD DXF CAD drawing parser (`DXFIngestor`, `DXFParsedFloorPlan`, `DXFEntity`).
  - **Parser Engine:** Uses `ezdxf` as the native DXF parsing engine for 2D CAD vector drawings.
  - **Supported CAD Entity Types:** Extracts `LWPOLYLINE`, `POLYLINE`, `LINE`, `ARC` (sampled arc vertices), and `CIRCLE` (sampled circle boundary ring) entities into 2D floating-point vertex coordinates.
  - **Layer Classification:** Deterministically classifies CAD layer names into domain spatial categories (`WALL`, `DOOR`, `WINDOW`, `COLUMN`, `FURNITURE`, `SPACE`, or `GENERIC` for unrecognized layers).
  - **Entity Count Semantics:** `total_entities_count` and `entities_by_category` reflect exact counts of extracted 2D vector CAD entities (`total_entities_count == len(extracted_entities) == sum(entities_by_category.values())`).
  - **Zero-Fabricated Geometry Policy:** No fake fallback geometry, mock entities, or invented coordinates exist. Missing files raise `FileNotFoundError`, missing `ezdxf` dependency raises `ImportError`, and malformed/unreadable DXF files raise `ValueError`.
  - **Fixture Testing:** Verified against real standard ASCII DXF fixture [`docs/fixtures/sample_floor_plan.dxf`](file:///d:/Layouts%20AI/docs/fixtures/sample_floor_plan.dxf).
- [`reconciliation.py`](file:///d:/Layouts%20AI/backend/app/bim/reconciliation.py): Authoritative floor plan geometry verification and anomaly report engine (`GeometryReconciler`, `GeometryVerificationReport`, `VerificationStatus`, `GeometryAnomalyWarning`).
  - **Shapely Topology Calculations:** Calculates total net floor area (`total_net_area_sqm`) and room counts directly from actual space polygon geometry operations (`poly.area` and `unary_union`). Zero hard-coded production geometry or fake fallback numbers exist (`no 240.0, 300.0, 375.0, or 20x12/25x15 demo boxes`).
  - **Outer Boundary Union:** Derives full topological outer perimeter geometry (`boundary_geometry`) preserving concavities, MultiPolygon components, and interior holes using Shapely `unary_union`.
  - **Anomaly Warning Detection:** Detects self-intersections, unclosed wall polylines, missing doors, missing walls, missing room geometries, and repaired polygons (`make_valid`).
  - **Human Verification Workflow:** Manages explicit `PENDING`, `VERIFIED`, and `REJECTED` state transitions. Verification requires Layouts Team RBAC role (`LAYOUT_EXEC`, `LAYOUT_MGR`, `ADMIN`). Rejection requires a mandatory rejection reason comment.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic v2 / JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*

