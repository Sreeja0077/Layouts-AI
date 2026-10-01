# API Module

## 📌 Purpose & Overview
Route definitions per resource and versioned API sub-routers.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/api`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Subdirectories
- `v1/`: Version 1 API routers.
  - [`projects.py`](file:///d:/Layouts%20AI/backend/app/api/v1/projects.py): Projects & floor plans CRUD endpoints.
    - **Why needed:** Manages high-level organizational project entities and floor plan revisions.
  - [`requirements.py`](file:///d:/Layouts%20AI/backend/app/api/v1/requirements.py): Requirement set parsing endpoints.
    - **Why needed:** Receives raw text/voice requirements and manages requirement state.
  - [`layout.py`](file:///d:/Layouts%20AI/backend/app/api/v1/layout.py): Layout proposal generation & edit endpoints.
    - **Why needed:** Triggers candidate optimization and handles iterative layout actions.
  - [`approvals.py`](file:///d:/Layouts%20AI/backend/app/api/v1/approvals.py): Revision approval workflow endpoints.
    - **Why needed:** Manages 4-role approval stage transitions and audit logging.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
