# Physical Validation Rules Engine

## 📌 Purpose & Overview
Deterministic architectural validation engine for space planning, furniture layout, circulation corridors, door swing arcs, and user requirements. Evaluates candidate layouts against 16 HARD rules and 4 SOFT rules.

## 🏗️ Architectural Role
- **Domain Layer:** `geometry/geo_engine/rules`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Subpackages
- [`rule_evaluator.py`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/rule_evaluator.py): Central evaluator executing 16 hard and 4 soft rules returning `ValidationResult`.
- [`base_rule.py`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/base_rule.py): Abstract base class `BaseRule` defining standard `evaluate()` interface.
- [`config.py`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/config.py): Configurable ruleset thresholds (aisle widths, clearances, gap limits).
- [`geometry/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/geometry/): `GeometryValidityRule`, `CollisionRule`, `ContainmentRule`, `FixedObjectIntegrityRule`.
- [`circulation/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/circulation/): `ClearanceRule`, `AisleWidthRule`, `AccessibilityRule`, `EgressRule`, `DoorSwingRule`, `EntranceObstructionRule`.
- [`requirements/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/requirements/): `RequirementComplianceRule`, `QuantityFulfillmentRule`, `CapacityRule`, `BundleIntegrityRule`.
- [`spatial/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/spatial/): `ZoneRule`, `ConnectivityRule`, `OrientationRule` (SOFT).
- [`design/`](file:///d:/Layouts%20AI/geometry/geo_engine/rules/design/): `WindowObstructionRule` (SOFT), `WallProximityRule` (SOFT), `NaturalLightRule` (SOFT).

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Read-only evaluation; no side effects on databases or layout state.
- Pure Python deterministic geometry engine independent from LLM.

---
*Maintained continuously across development tasks.*
