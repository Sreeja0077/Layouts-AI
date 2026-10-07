# Editor State Module (Task 5.4)

## 📌 Purpose & Overview
Provides transient UI interaction state management (`selection`, `interactionMode`, `activeSnapGuides`).

## 🔒 Architectural Invariants
- **Transient UI State Only:** Stores local selection and transform mode. Does NOT duplicate or replace authoritative backend geometry.
