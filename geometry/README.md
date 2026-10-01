# Deterministic Geometry & Optimization Engine

## 📌 Purpose & Overview
Pure Python package (zero web framework, zero LLM dependencies) handling all spatial validation, obstacle subtraction, placement optimization, circulation checks, and materialization.

## 🏗️ Architectural Role
- **Domain Layer:** `geometry`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Responsibilities
- [`__init__.py`](file:///d:/Layouts%20AI/geometry/__init__.py): Package entry point for geometry package.

## 📁 Related Subdirectories & Responsibilities
- [`geo_engine/`](file:///d:/Layouts%20AI/geometry/geo_engine/): Core spatial operations, free-space calculation, hard rules, and CP-SAT solvers.
- [`tests/`](file:///d:/Layouts%20AI/geometry/tests/): Unit tests for geometry engine algorithms.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
