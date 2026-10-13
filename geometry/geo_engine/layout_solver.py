"""
Authoritative Deterministic Layout Solver Engine (Phase 9).
Performs deterministic layout reconfiguration & optimization within authoritative architectural geometry
and validated user selected regions.

CRITICAL INVARIANTS:
1. Reconfigures the selected portion of current layout (existing items are part of optimization).
2. SOLD_FIXED (red) items are strictly immutable (cannot move, rotate, resize, delete, or collide).
3. AVAILABLE_MOVABLE (green) items can relocate/rotate, preserving stable source object IDs without duplication.
4. Outer perimeter walls and structural columns are ALWAYS fixed.
5. Internal walls are preserved by default; outer concrete walls never enter optimizer as movable.
6. Selected region (intersected with room) is authoritative solving scope.
7. Coordinates generated strictly by deterministic Python optimization (CP-SAT / Heuristic). LLM never generates coordinates.
8. Dynamic candidate count: 0..N valid distinct candidates. Near-identical layouts deduplicated via spatial signatures.
9. Infeasible requests return explicit structured InfeasibilityReport (candidate count = 0); never return partial layouts.
"""

import hashlib
import math
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from shapely.geometry import MultiPolygon, Point, Polygon, box
    from shapely.ops import unary_union
    from shapely.validation import make_valid
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

from app.domain.geometry.entities import (
    ColumnEntity,
    DoorEntity,
    ExistingFurnitureEntity,
    MovabilityStatus,
    RoomEntity,
    WallEntity,
    WindowEntity,
)
from app.domain.layout.schemas import (
    CirculationPath,
    GenerateLayoutResponse,
    InfeasibilityReport,
    LayoutMetrics,
    LayoutSuggestion,
    PlacedObject,
)
from app.domain.requirements.schemas import RequirementItem, RequirementSet
from geometry.geo_engine.circulation import CirculationEngine
from geometry.geo_engine.freespace import FreeSpaceEngine
from geometry.geo_engine.optimizer_cpsat import CPSATLayoutOptimizer
from geometry.geo_engine.optimizer_heuristic import HeuristicLayoutOptimizer
from geometry.geo_engine.rules.circulation.clearance_rule import ClearanceRule
from geometry.geo_engine.rules.geometry.collision_rule import CollisionRule
from geometry.geo_engine.rules.rule_evaluator import RuleEvaluator
from geometry.geo_engine.strategies import ALL_STRATEGIES, StrategyTemplate, get_all_strategies, get_strategy


# ==============================================================================
# TEMPORARY TEST / PROTOTYPE DEFAULTS ONLY (Deprecated).
# NOT authoritative production truth.
# Authoritative physical catalog definitions are owned by PostgreSQL and accessed via:
# app.domain.catalog.catalog_service.CatalogService
# ==============================================================================
DEFAULT_FURNITURE_CATALOG: Dict[str, Dict[str, Any]] = {
    "PROFESSIONAL_DESK": {"width": 1.5, "depth": 0.75, "clearance_back": 0.8, "item_type": "PROFESSIONAL_DESK"},
    "EXECUTIVE_DESK": {"width": 1.8, "depth": 0.9, "clearance_back": 0.9, "item_type": "EXECUTIVE_DESK"},
    "MANAGER_DESK": {"width": 1.8, "depth": 0.9, "clearance_back": 0.9, "item_type": "MANAGER_DESK"},
    "WORKSTATION": {"width": 1.4, "depth": 0.7, "clearance_back": 0.7, "item_type": "WORKSTATION"},
    "TASK_CHAIR": {"width": 0.6, "depth": 0.6, "clearance_back": 0.2, "item_type": "TASK_CHAIR"},
    "CONFERENCE_TABLE": {"width": 2.4, "depth": 1.2, "clearance_back": 0.8, "item_type": "CONFERENCE_TABLE"},
    "STORAGE_CABINET": {"width": 1.0, "depth": 0.5, "clearance_back": 0.3, "item_type": "STORAGE_CABINET"},
    "SOFA": {"width": 1.8, "depth": 0.8, "clearance_back": 0.3, "item_type": "SOFA"},
    "GENERIC": {"width": 1.2, "depth": 0.6, "clearance_back": 0.5, "item_type": "GENERIC"},
}


def compute_spatial_signature(
    placed_objects: List[PlacedObject],
    precision_grid_m: float = 0.05,
) -> str:
    """
    Computes a deterministic hash signature of a spatial layout configuration.
    Normalizes coordinates and rotations to avoid floating point jitter.
    Sorts elements canonically so object list order does not affect uniqueness.
    """
    elements = []
    for obj in placed_objects:
        norm_x = round(round(obj.x / precision_grid_m) * precision_grid_m, 2)
        norm_y = round(round(obj.y / precision_grid_m) * precision_grid_m, 2)
        norm_rot = int(round(obj.rotation_deg)) % 360
        norm_w = round(obj.width, 2)
        norm_h = round(obj.height, 2)
        norm_type = obj.item_type.upper()
        ref_id = obj.source_object_id or norm_type
        is_rel = "1" if obj.is_relocated else "0"
        is_new = "1" if obj.is_new else "0"

        elements.append((norm_type, ref_id, norm_x, norm_y, norm_rot, norm_w, norm_h, is_rel, is_new))

    elements.sort()
    sig_str = ";".join(
        f"{e[0]}:{e[1]}:{e[2]:.2f},{e[3]:.2f}@{e[4]}:{e[5]:.2f}x{e[6]:.2f}:{e[7]}:{e[8]}"
        for e in elements
    )
    return hashlib.sha256(sig_str.encode("utf-8")).hexdigest()[:16]


class DeterministicLayoutSolver:
    """
    Deterministic Spatial Layout Reconfiguration & Optimization Solver.
    """

    def __init__(
        self,
        catalog: Optional[Dict[str, Dict[str, Any]]] = None,
        db_session: Optional[Any] = None,
    ):
        # Incorporate authoritative catalog definitions if db_session is provided
        authoritative_specs: Dict[str, Dict[str, Any]] = {}
        if db_session is not None:
            try:
                from app.domain.catalog.catalog_service import CatalogService
                items = CatalogService.list_catalog_items(db_session)
                for it in items:
                    key = (it.subtype or it.name or it.catalog_item_id).upper().replace(" ", "_")
                    authoritative_specs[key] = {
                        "width": it.width_m,
                        "depth": it.depth_m,
                        "clearance_back": it.clearance.back_m if it.clearance else 0.5,
                        "item_type": it.subtype or it.category.value if hasattr(it.category, "value") else str(it.category),
                        "catalog_item_id": it.catalog_item_id,
                    }
            except Exception:
                pass

        self.catalog = {**DEFAULT_FURNITURE_CATALOG, **authoritative_specs, **(catalog or {})}
        self.evaluator = RuleEvaluator()
        self.cpsat_optimizer = CPSATLayoutOptimizer(self.catalog)
        self.heuristic_optimizer = HeuristicLayoutOptimizer(self.catalog)

    def get_catalog_entry(self, item_type: str) -> Dict[str, Any]:
        """Lookup physical world metric footprint dimensions for an item type."""
        key = item_type.upper().replace(" ", "_")
        if key in self.catalog:
            return self.catalog[key]
        for c_key, c_val in self.catalog.items():
            if c_key in key or key in c_key:
                return c_val
        return self.catalog["GENERIC"]

    def extract_obstacles(
        self,
        room: RoomEntity,
        allow_internal_wall_moves: bool = False,
    ) -> List[Polygon]:
        """
        Extract authoritative 2D obstacle polygons from room architectural elements:
        perimeter concrete walls, structural columns, interior walls, and door swing arcs.
        """
        obstacles: List[Polygon] = []

        # 1. Structural Walls
        walls = getattr(room, "walls", None) or []
        for wall in walls:
            # If wall is internal partition and moves are explicitly allowed, skip from rigid obstacle list
            is_internal_movable = (
                not wall.is_exterior
                and getattr(wall, "movability_status", None) == MovabilityStatus.INTERNAL_WALL_MOVABLE
            )
            if allow_internal_wall_moves and is_internal_movable:
                continue

            p1, p2 = wall.start_point, wall.end_point
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length > 0.001:
                nx, ny = -dy / length, dx / length
                ht = wall.thickness_m / 2.0
                wall_poly = Polygon([
                    (p1[0] - nx * ht, p1[1] - ny * ht),
                    (p2[0] - nx * ht, p2[1] - ny * ht),
                    (p2[0] + nx * ht, p2[1] + ny * ht),
                    (p1[0] + nx * ht, p1[1] + ny * ht),
                ])
                obstacles.append(wall_poly)

        # 2. Doors (Swing Arc + Approach Zone)
        if room.doors:
            for door in room.doors:
                swing_verts = door.get_swing_arc_polygon()
                if len(swing_verts) >= 3:
                    obstacles.append(Polygon(swing_verts))

                cx, cy = door.center_x, door.center_y
                r = max(0.5, door.width_m / 2.0 + 0.2)
                door_clearance_poly = Polygon([
                    (cx - r, cy - r),
                    (cx + r, cy - r),
                    (cx + r, cy + r),
                    (cx - r, cy + r),
                ])
                obstacles.append(door_clearance_poly)

        # 3. Structural Columns
        if room.columns:
            for col in room.columns:
                col_verts = col.get_obstacle_polygon()
                if len(col_verts) >= 3:
                    obstacles.append(Polygon(col_verts))

        return [obs for obs in obstacles if not obs.is_empty and obs.is_valid]

    def solve_reconfiguration(
        self,
        floor_plan_id: str,
        room: RoomEntity,
        requested_items: List[Dict[str, Any]],
        requirements_set: Optional[RequirementSet] = None,
        selected_region_polygon: Optional[List[Tuple[float, float]]] = None,
        max_candidates: int = 20,
        solver_mode: str = "AUTO",
        allow_internal_wall_moves: bool = False,
    ) -> GenerateLayoutResponse:
        """
        Core Phase 9 Layout Reconfiguration & Optimization Engine.
        Returns complete GenerateLayoutResponse with dynamic 0..N candidates and InfeasibilityReport if 0 candidates.
        """
        if not HAS_SHAPELY:
            raise RuntimeError("Shapely is required for DeterministicLayoutSolver.")

        # 1. Authoritative Solving Scope: room_boundary INTERSECT selected_region
        room_poly = Polygon(room.boundary_polygon)
        if not room_poly.is_valid:
            room_poly = make_valid(room_poly)

        effective_scope = room_poly
        if selected_region_polygon and len(selected_region_polygon) >= 3:
            user_poly = Polygon(selected_region_polygon)
            if not user_poly.is_valid:
                user_poly = make_valid(user_poly)

            clipped = room_poly.intersection(user_poly)
            if clipped.is_empty or clipped.area < 0.1:
                # Infeasible scope: selected region has zero overlap with room
                return GenerateLayoutResponse(
                    success=False,
                    candidate_count=0,
                    candidates=[],
                    infeasibility_report=InfeasibilityReport(
                        is_feasible=False,
                        candidate_count=0,
                        requested_items=requested_items,
                        selected_region_polygon=selected_region_polygon,
                        usable_area_sqm=0.0,
                        reasons=["Selected user region has zero overlap with authoritative room boundary."],
                        violated_constraints=["REGION_CONTAINMENT", "MINIMUM_AREA"],
                    ),
                )
            # If multi-polygon, select contiguous component with largest area
            if clipped.geom_type == "MultiPolygon":
                effective_scope = max(clipped.geoms, key=lambda g: g.area)
            else:
                effective_scope = clipped

        # 2. Partition Existing Furniture into SOLD_FIXED vs AVAILABLE_MOVABLE
        fixed_sold_objects: List[PlacedObject] = []
        movable_existing_items: List[ExistingFurnitureEntity] = []

        all_existing = getattr(room, "existing_furniture", None) or []
        for ef in all_existing:
            status = getattr(ef, "movability_status", None)
            is_sold = (
                status == MovabilityStatus.SOLD_FIXED
                or status == "SOLD_FIXED"
                or (getattr(ef, "keep_flag", True) and status != MovabilityStatus.AVAILABLE_MOVABLE and status != "AVAILABLE_MOVABLE")
            )

            cat_info = self.get_catalog_entry(ef.catalog_item_id)
            w = getattr(ef, "width_m", None) or cat_info["width"]
            d = getattr(ef, "depth_m", None) or cat_info["depth"]

            if is_sold:
                fixed_sold_objects.append(
                    PlacedObject(
                        id=ef.id,
                        catalog_item_id=ef.catalog_item_id,
                        item_type=cat_info["item_type"],
                        x=ef.position[0],
                        y=ef.position[1],
                        rotation_deg=ef.rotation,
                        width=float(w),
                        height=float(d),
                        clearance_back=float(cat_info.get("clearance_back", 0.5)),
                        locked=True,
                        source_object_id=ef.id,
                        is_relocated=False,
                        is_new=False,
                        movability_status="SOLD_FIXED",
                    )
                )
            else:
                movable_existing_items.append(ef)

        # 3. Extract Architectural Obstacles & Calculate Usable Geometry
        obstacles = self.extract_obstacles(room, allow_internal_wall_moves=allow_internal_wall_moves)

        # Fixed sold objects are solid physical obstacles
        for fixed_obj in fixed_sold_objects:
            obstacles.append(CollisionRule.get_object_polygon(fixed_obj))

        scope_vertices = [(round(x, 4), round(y, 4)) for x, y in effective_scope.exterior.coords]
        usable_geom = FreeSpaceEngine.compute_usable_geometry(
            room_polygon=scope_vertices,
            obstacles=obstacles,
            wall_inset_buffer=0.15,
            obstacle_clearance_buffer=0.05,
        )

        # 4. Check Preliminary Usable Area Infeasibility
        # Compute total minimum required area for requested items
        total_req_area = 0.0
        for r in requested_items:
            cat = self.get_catalog_entry(r.get("item_type", "GENERIC"))
            rw = float(r.get("width_m") or cat["width"])
            rd = float(r.get("depth_m") or cat["depth"])
            total_req_area += rw * rd * int(r.get("quantity", 1))

        for m in movable_existing_items:
            cat = self.get_catalog_entry(m.catalog_item_id)
            mw = float(getattr(m, "width_m", None) or cat["width"])
            md = float(getattr(m, "depth_m", None) or cat["depth"])
            total_req_area += mw * md

        if usable_geom.is_empty or usable_geom.area < 0.3 or (usable_geom.area < total_req_area * 0.9):
            reasons = [
                f"Selected region has insufficient usable floor area ({usable_geom.area:.2f} sqm) "
                f"to accommodate requested program (requires ~{total_req_area:.2f} sqm plus clearances)."
            ]
            return GenerateLayoutResponse(
                success=False,
                candidate_count=0,
                candidates=[],
                infeasibility_report=InfeasibilityReport(
                    is_feasible=False,
                    candidate_count=0,
                    requested_items=requested_items,
                    selected_region_polygon=selected_region_polygon,
                    usable_area_sqm=round(usable_geom.area, 2) if not usable_geom.is_empty else 0.0,
                    reasons=reasons,
                    violated_constraints=["USABLE_AREA_DEFICIT", "MINIMUM_CLEARANCE"],
                ),
            )

        # 5. Execute Multi-Strategy Optimization (CP-SAT + Heuristic Fallback)
        strategies: List[StrategyTemplate] = get_all_strategies()
        seen_signatures: Set[str] = set()
        valid_candidates: List[LayoutSuggestion] = []

        doors = getattr(room, "doors", None) or []

        for strat in strategies:
            if len(valid_candidates) >= max_candidates:
                break

            strat_candidates: List[LayoutSuggestion] = []

            # A) Attempt OR-Tools CP-SAT if enabled/available
            if solver_mode.upper() in ("AUTO", "CPSAT") and self.cpsat_optimizer.is_available():
                cpsat_results = self.cpsat_optimizer.optimize(
                    floor_plan_id=floor_plan_id,
                    room=room,
                    usable_geom=usable_geom,
                    obstacles=obstacles,
                    doors=doors,
                    fixed_objects=fixed_sold_objects,
                    movable_existing=movable_existing_items,
                    requested_items=requested_items,
                    strategy=strat,
                    selected_region_polygon=selected_region_polygon,
                    max_solutions=3,
                )
                strat_candidates.extend(cpsat_results)

            # B) If CP-SAT produced 0 candidates for this strategy, run Heuristic Fallback
            if not strat_candidates and solver_mode.upper() in ("AUTO", "HEURISTIC"):
                heur_cand = self.heuristic_optimizer.optimize(
                    floor_plan_id=floor_plan_id,
                    room=room,
                    usable_geom=usable_geom,
                    obstacles=obstacles,
                    doors=doors,
                    fixed_objects=fixed_sold_objects,
                    movable_existing=movable_existing_items,
                    requested_items=requested_items,
                    strategy=strat,
                    selected_region_polygon=selected_region_polygon,
                )
                if heur_cand:
                    strat_candidates.append(heur_cand)

            # C) Deduplicate Candidates using Spatial Signatures
            for cand in strat_candidates:
                sig = compute_spatial_signature(cand.placed_objects)
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)
                cand.spatial_signature = sig
                valid_candidates.append(cand)
                if len(valid_candidates) >= max_candidates:
                    break

        # 6. Verify Requirement Quantity Preservation (Rule: Never partially fulfill)
        total_expected_new = sum(int(r.get("quantity", 1)) for r in requested_items)
        total_expected_movable = len(movable_existing_items)
        total_expected_fixed = len(fixed_sold_objects)
        total_expected_all = total_expected_new + total_expected_movable + total_expected_fixed

        filtered_candidates: List[LayoutSuggestion] = []
        for cand in valid_candidates:
            if len(cand.placed_objects) == total_expected_all:
                filtered_candidates.append(cand)

        # 7. Final Response Assembly: 0..N Candidates or Explicit Infeasibility
        if not filtered_candidates:
            reasons = [
                f"No complete spatial configuration satisfying all clearance, collision, and door egress rules "
                f"could be resolved for {total_expected_new} requested items in the specified region ({usable_geom.area:.2f} sqm usable)."
            ]
            return GenerateLayoutResponse(
                success=False,
                candidate_count=0,
                candidates=[],
                infeasibility_report=InfeasibilityReport(
                    is_feasible=False,
                    candidate_count=0,
                    requested_items=requested_items,
                    selected_region_polygon=selected_region_polygon,
                    usable_area_sqm=round(usable_geom.area, 2),
                    reasons=reasons,
                    violated_constraints=["SPATIAL_SOLVER_INFEASIBLE", "QUANTITY_FULFILLMENT"],
                ),
            )

        return GenerateLayoutResponse(
            success=True,
            candidate_count=len(filtered_candidates),
            candidates=filtered_candidates,
            infeasibility_report=None,
        )

    def solve_layout_candidates(
        self,
        floor_plan_id: str,
        room: RoomEntity,
        requested_items: List[Dict[str, Any]],
        requirements_set: Optional[RequirementSet] = None,
        max_candidates: int = 20,
        selected_region_polygon: Optional[List[Tuple[float, float]]] = None,
    ) -> List[LayoutSuggestion]:
        """
        Public solver method returning dynamic 0..N LayoutSuggestion list.
        Maintains backward compatibility with callers expecting List[LayoutSuggestion].
        """
        response = self.solve_reconfiguration(
            floor_plan_id=floor_plan_id,
            room=room,
            requested_items=requested_items,
            requirements_set=requirements_set,
            selected_region_polygon=selected_region_polygon,
            max_candidates=max_candidates,
        )
        return response.candidates
