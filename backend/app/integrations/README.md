# Integrations Module

## 📌 Purpose & Overview
Manages external service clients (LLM gateway via LiteLLM, Keycloak OIDC authentication).

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/integrations`
- **System Authority:** External API abstraction layer; decouples core application code from specific vendor implementations.

## 🔒 Security & Quality Invariants
- All external API access is audited and strictly typed.
- Pydantic contracts are enforced across service boundaries.

---
*Maintained continuously across development tasks.*
