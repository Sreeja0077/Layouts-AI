# Performance & Load Testing (Locust/k6)

## 📌 Purpose & Overview
Locust and k6 performance scripts testing spatial query response times, concurrent candidate generation, and WebSocket streaming.

## 🏗️ Architectural Role
- **Domain Layer:** `tests/load`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Related Subdirectories & Responsibilities
This directory contains modular components structured according to the *AI-Assisted Office Layout Generation Platform Deep Architecture Blueprint*.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Generated based on Blueprint Section 27 (Complete Folder Structure).*
