# Geometry Core Engine Modules

## 📌 Purpose & Overview
Shapely-based free-space calculation, OR-Tools CP-SAT solver, heuristic packing routines, circulation graph checks, physical validation rules, layout compiler/materializer, and visual diff algorithms.

## 🏗️ Architectural Role
- **Domain Layer:** `geometry/geo_engine`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Responsibilities
- [`freespace.py`](file:///d:/Layouts%20AI/geometry/geo_engine/freespace.py): 2D Free-space calculation engine (`FreeSpaceEngine`).
  - **Why needed:** Applies perimeter wall insets and subtracts structural obstacles (columns, internal walls) and door clearance zones to compute net placement polygons.

## 📁 Related Subdirectories & Responsibilities
- [`rules/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/): Spatial hard-constraint validation rules (collision, clearance, door swing arcs).
- [`strategies/`](file:///d:/Layouts%20AI/geometry/geo_engine/strategies/): High-level placement strategy templates.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
