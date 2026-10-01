# Requirements Domain Module

## 📌 Purpose & Overview
Manages RequirementSet representations, company-default fallback rules, and completeness validation.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/domain/requirements`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Responsibilities
- [`schemas.py`](file:///d:/Layouts%20AI/backend/app/domain/requirements/schemas.py): Pydantic v2 domain schemas (`RequirementSet`, `RequirementItem`, `SpatialPreference`, `RequirementStatus`, `ResolutionMethod`).
  - **Why needed:** Provides strict typing and JSON schema contracts for parsing, normalizing, and storing spatial requirements extracted from user text/voice input.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
