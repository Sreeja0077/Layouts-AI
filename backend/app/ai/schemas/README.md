# AI Schemas Module

## 📌 Purpose & Overview
Pydantic structured-output models used by LangGraph nodes and LiteLLM LLM providers.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/ai/schemas`
- **System Authority:** Deterministic Python owns geometry & state; AI proposes intent; PostGIS stores authoritative truth.

## 📁 Files & Responsibilities
- [`structured_output.py`](file:///d:/Layouts%20AI/backend/app/ai/schemas/structured_output.py): LLM structured output models (`ParsedRequirementOutput`, `ClarificationRequest`, `PlanningStrategyList`, `ChangeInterpreterOutput`).
  - **Why needed:** Guarantees strict JSON schema validation when LLMs emit requirements, clarification questions, candidate strategies, or edit actions.

## 🔒 Security & Quality Invariants
- All state-changing operations are audited and validated.
- Strict typing and Pydantic/JSON Schema contracts are enforced.
- No direct LLM access to authoritative database writes or final coordinate math.

---
*Maintained continuously across development tasks.*
