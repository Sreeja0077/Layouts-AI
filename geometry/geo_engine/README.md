# Geometry Core Engine Modules

## 📌 Purpose & Overview
Provides deterministic 2D free-space geometry calculation (`FreeSpaceEngine`), physical layout validation rules, placement strategy templates, and geometric operations. Serves as the mathematical substrate for later CP-SAT optimization and circulation graph analysis.

## 🏗️ Architectural Role
- **Domain Layer:** `geometry/geo_engine`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📐 FreeSpaceEngine (Task 4.1 Implementation)
- **Authoritative Substrate:** Powered strictly by Shapely / GEOS (`compute_usable_geometry`, `compute_usable_freespace`, `calculate_freespace_area`). No pure-Python rectangular bounding-box approximations or fake fallbacks. If Shapely is missing, raises an explicit `ImportError`.
- **Perimeter Wall Inset:** Applies safety offsets (`wall_inset_buffer`) directly to 2D room boundaries while preserving concave geometries (L-shaped and U-shaped rooms).
- **Obstacle Subtraction:** Union-based subtraction of structural columns, internal walls, and door swing arc polygons (`DoorEntity.get_swing_arc_polygon()`).
- **Obstacle Clearance Buffers:** Expands obstacles with `obstacle_clearance_buffer` before subtraction.
- **Topology Preservation:** Full preservation of interior rings (holes) and `MultiPolygon` components. Disconnected usable regions produced by barriers retain all components and correct total area (`geometry.area`).
- **Deterministic & Precise:** Pure GEOS floating-point operations in 2D world coordinates (meters). Zero randomness or rounding jitter.

## 📁 Files & Related Subdirectories
- [`freespace.py`](file:///d:/Layouts%20AI/geometry/geo_engine/freespace.py): Authoritative 2D Free-space calculation engine (`FreeSpaceEngine`).
- [`rules/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/): Spatial hard-constraint and soft-design validation rules (20 deterministic rules).
- [`strategies/`](file:///d:/Layouts%20AI/geometry/geo_engine/strategies/): High-level placement strategy templates.

## 🔒 Security & Quality Invariants
- Deterministic Python geometry calculations; zero fabricated geometry.
- Strict typing and Pydantic/JSON Schema contracts enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
