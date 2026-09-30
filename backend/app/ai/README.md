# AI Orchestration & Workflow

## 📌 Purpose & Overview
AI sub-system containing LangGraph workflow graphs, specialized LLM nodes, prompt templates, structured output schemas, tool wrappers, and LiteLLM gateway integrations.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/ai`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Related Subdirectories & Responsibilities
This directory contains modular components structured according to the *AI-Assisted Office Layout Generation Platform Deep Architecture Blueprint*.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Generated based on Blueprint Section 27 (Complete Folder Structure).*
