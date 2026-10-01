# Revisions & Versioning Module

## 📌 Purpose & Overview
Manages append-only operation patches, floor plan source version publishing, and visual diff reconstruction.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/domain/revisions`
- **System Authority:** Versioning authority for floor plan source baselines (`FloorPlanSourceVersion`) and append-only patch operation history.

## 📁 Files & Responsibilities
- [`versioning.py`](file:///d:/Layouts%20AI/backend/app/domain/revisions/versioning.py): Source versioning & publishing engine (`SourceVersionPublisher`, `FloorPlanSourceVersionPayload`).
  - **Why needed:** Manages floor plan source version publishing (`version_no`, locked baseline snapshot, `is_published`) to prevent past layout designs from drifting when floor plan blueprints are updated.

## 🔒 Security & Quality Invariants
- Published source versions (`is_published=True`) are immutable and read-only.
- All version changes track the publishing user ID and timestamp.

---
*Maintained continuously across development tasks.*
