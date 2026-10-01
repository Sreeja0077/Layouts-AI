# Security & Authorization Module

## 📌 Purpose & Overview
Manages Keycloak OIDC authentication, JWT token verification, and Role-Based Access Control (RBAC) middleware guards.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/security`
- **System Authority:** Server-side authentication and role enforcement; multi-tenant organization boundaries (`org_id`).

## 📁 Files & Responsibilities
- [`config.py`](file:///d:/Layouts%20AI/backend/app/security/config.py): Security & Auth environment configuration (`JWT_SECRET_KEY`, `KEYCLOAK_URL`, `ALLOW_MOCK_AUTH`).
  - **Why needed:** Provides centralized authentication settings and local dev bypass flags.
- [`auth.py`](file:///d:/Layouts%20AI/backend/app/security/auth.py): Token decoding and user context dependency (`get_current_user`, `AuthenticatedUser`, `UserRole`).
  - **Why needed:** Extracts authenticated user identity (`user_id`, `email`, `role`, `org_id`) from incoming HTTP `Authorization: Bearer <token>` headers.
- [`rbac.py`](file:///d:/Layouts%20AI/backend/app/security/rbac.py): Role-Based Access Control guards (`RoleChecker`, `require_roles`).
  - **Why needed:** Enforces permissions across 4 platform roles (`SALES_EXEC`, `LAYOUT_EXEC`, `LAYOUT_MGR`, `SALES_MGR`) on restricted API routes.

## 🔒 Security & Quality Invariants
- Every state-changing operation checks authenticated user permissions.
- Multi-tenant organization boundaries (`org_id`) are strictly enforced.
- Client-side UI button hiding is a convenience; all access decisions are enforced server-side.

---
*Maintained continuously across development tasks.*
