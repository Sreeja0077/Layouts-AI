# Layout Domain Module

## 📌 Purpose & Overview
Defines LayoutSuggestion, PlacedObject, LayoutAction, and Revision domain models.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/domain/layout`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Responsibilities
- [`schemas.py`](file:///d:/Layouts%20AI/backend/app/domain/layout/schemas.py): Pydantic v2 schemas (`LayoutSuggestion`, `PlacedObject`, `CirculationPath`, `LayoutMetrics`, `LayoutAction`, `ActionType`, `Polygon2D`, `BoundingBox2D`).
  - **Why needed:** Defines the exact coordinate and metric payload structure for candidate layout proposals and structured semantic edit instructions (`LayoutAction`).

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
