# 2D Canvas Floor Plan Editor

## 📌 Purpose & Overview
Interactive floor plan editor built with react-konva, supporting drag-and-drop, object rotation, resizing, wall snapping, dimension lines, and freehand polygon creation.

## 🏗️ Architectural Role
- **Domain Layer:** `frontend/src/editor`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Related Subdirectories & Responsibilities
This directory contains modular components structured according to the *AI-Assisted Office Layout Generation Platform Deep Architecture Blueprint*.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Generated based on Blueprint Section 27 (Complete Folder Structure).*
