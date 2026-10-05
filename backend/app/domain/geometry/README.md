# Geometry Domain Module

## 📌 Purpose & Overview
Provides canonical 2D architectural BIM entity models, spatial boundary representations, and geometry validation contracts. The domain layer establishes a stable, renderer-independent, and AI-independent canonical geometry representation consumed by layout generation, spatial validation, free-space analysis, and editing.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/domain/geometry`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📐 Core Canonical Entities (Task 3.1)
- [`WallEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L22): Interior partitions and exterior load-bearing walls.
- [`DoorEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L33): Openings with 2D swing arc polygon calculation (`get_swing_arc_polygon`).
- [`WindowEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L64): Openings providing natural light and wall boundaries.
- [`ColumnEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L76): Structural pillars with safety clearance buffer polygons (`get_obstacle_polygon`).
- [`BeamEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L101): Overhead structural beam projections.
- [`ExistingFurnitureEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L110): Furniture extracted from source BIM/CAD plans. Carries `keep_flag` semantics (`True` = retained/locked from source plan, `False` = movable/removable).
- [`RoomEntity`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L121): Spatial boundaries with net area in square meters and relationships to contained doors, windows, columns, and existing furniture.
- [`CanonicalFloorPlan`](file:///d:/Layouts%20AI/backend/app/domain/geometry/entities.py#L139): Aggregated canonical floor plan holding rooms, structural constraints, and source existing furniture.

## 📏 Coordinate & Unit Conventions
- **Length / Distance:** Meters (`m`), e.g., `width_m`, `thickness_m`, `clearance_buffer_m`.
- **Area:** Square meters (`sqm`), e.g., `net_area_sqm`.
- **Angles / Rotation:** Degrees (`deg`), e.g., `swing_deg`, `rotation`.
- **Coordinates:** 2D Cartesian world coordinates `(x, y)` in meters.

## 🔄 Distinction: Existing Furniture vs. Placed Furniture
- **`ExistingFurnitureEntity` (Source Plan):** Represents furniture present in the source IFC/DXF file. Retained or marked movable via `keep_flag`.
- **`PlacedObject` / Placed Furniture (Layout Generation):** Represents new furniture placed during downstream AI/algorithmic layout optimization (Phase 4+).

## 🚫 Out of Scope for Task 3.1 (Belongs to Later Tasks)
- Furniture catalog resolver and item lookup
- CP-SAT / LP layout optimizer engine
- LLM / natural language requirement parser
- Revision engine & approval workflow
- Frontend interactive canvas editor

## 🔒 Security & Quality Invariants
- All models use Pydantic v2 with `extra="forbid"`.
- Strict typing and explicit metric units are enforced.
- Deterministic Python geometry calculations; zero fabricated source geometry.

---
*Maintained continuously across development tasks.*
