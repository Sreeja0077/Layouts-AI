# Persistence Module

## 📌 Purpose & Overview
Manages database models, PostGIS geometry write-through synchronization, database connection sessions, and repositories.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/persistence`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Responsibilities
- [`models.py`](file:///d:/Layouts%20AI/backend/app/persistence/models.py): SQLAlchemy 2.0 ORM model definitions (`User`, `Project`, `FloorPlan`, `Region`, `RequirementSetModel`, `LayoutSuggestionModel`, `Revision`, `Approval`).
  - **Why needed:** Provides object-relational mapping to PostgreSQL + PostGIS transactional tables.
- [`database.py`](file:///d:/Layouts%20AI/backend/app/persistence/database.py): Engine configuration, `SessionLocal` factory, `get_db()` dependency, and health check probes.
  - **Why needed:** Manages database connection pooling, transactional session lifecycles, and dependency injection into FastAPI routes.
- [`postgis_sync.py`](file:///d:/Layouts%20AI/backend/app/persistence/postgis_sync.py): PostGIS WKT geometry generator and spatial containment/intersection engine (`PostGISGeometrySync`).
  - **Why needed:** Synchronizes rich JSONB object records with PostGIS spatial geometry columns (`polygon_geom`) for GiST-indexed spatial queries and containment checks.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
