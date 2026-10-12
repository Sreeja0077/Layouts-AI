# Specialized AI Nodes

## 📌 Purpose & Overview
Discrete LLM and deterministic nodes powering the AI reasoning pipeline:
- **`RequirementParser` (Task 8.1)**: Translates natural language into structured semantic `RequirementSet` models.
- **`AmbiguityClassifier` (Task 8.2)**: Evaluates semantic clarity and determines when clarification questions are needed.

## 🏗️ Architectural Boundary: Semantic vs. Physical Catalog Resolution
- **Semantic Intent Only**: In Phase 8, `RequirementParser` extracts user intent (space type, semantic items, quantities, spatial preferences).
- **Phase 7 Decoupling**: Physical furniture catalogs, Revit families, and 3D mesh dimensions are intentionally pending Phase 7. `resolved_catalog_item_id` and `resolution_method` remain `None`. Zero dimensions or Revit families are fabricated.
- **System Authority**: Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative spatial truth.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated via Pydantic v2 schemas.
- Strict typing and JSON Schema contracts are enforced (`ParsedRequirementOutput`).
- No direct LLM access to authoritative database writes or coordinate math.
- Mock providers are available for completely offline, deterministic testing.
