# Alembic Database Migrations

## 📌 Purpose & Overview
Manages version-controlled schema migrations for PostgreSQL + PostGIS database tables.

## 🏗️ Architectural Role
- **Domain Layer:** `backend/alembic`
- **System Authority:** Schema evolution authority for database tables, spatial indexes, and extensions (`postgis`, `vector`).

## 📁 Files & Responsibilities
- [`schema_draft.sql`](file:///d:/Layouts%20AI/backend/alembic/schema_draft.sql): Raw PostgreSQL + PostGIS DDL reference script.
  - **Why needed:** Provides a single, clean SQL reference script for database initialization.
- [`env.py`](file:///d:/Layouts%20AI/backend/alembic/env.py): Migration execution context.
  - **Why needed:** Connects Alembic runner to SQLAlchemy `Base.metadata` and environment connection strings.
- [`versions/001_initial_postgis_schema.py`](file:///d:/Layouts%20AI/backend/alembic/versions/001_initial_postgis_schema.py): Initial database migration script.
  - **Why needed:** Enables PostGIS & pgvector extensions and sets up initial transactional schema revisions.

## 🔒 Security & Quality Invariants
- Migrations must always run within database transactions.
- Schema changes are tracked in version control before applying to production.

---
*Maintained continuously across development tasks.*
