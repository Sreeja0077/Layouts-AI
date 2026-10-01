-- =============================================================================
-- AI-Assisted Office Layout Generation Platform - Draft Database Schema
-- Target: PostgreSQL 16 + PostGIS 3.4 + pgvector 0.7+
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "vector";

-- -----------------------------------------------------------------------------
-- 1. Identity & Role-Based Access Control (RBAC)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('SALES_EXEC', 'LAYOUT_EXEC', 'LAYOUT_MGR', 'SALES_MGR', 'ADMIN')),
    org_id UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. Organizational Hierarchy (Projects, Buildings, Floor Plans)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    org_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS floor_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    building_name VARCHAR(255),
    floor_number INT DEFAULT 1,
    current_working_revision_id UUID,
    current_published_revision_id UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS floor_plan_source_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('IFC', 'DXF', 'PDF', 'RASTER_IMAGE')),
    file_storage_path VARCHAR(1024) NOT NULL,
    ifc_export_metadata JSONB DEFAULT '{}'::jsonb,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 3. Freehand Working Regions (PostGIS Polygons)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
    name VARCHAR(255) DEFAULT 'Selected Region',
    polygon_geom GEOMETRY(Polygon, 0) NOT NULL, -- Spatial 2D geometry in floor plan coordinates
    polygon_json JSONB NOT NULL,
    area_sqm NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 4. Furniture Catalog & Bundles (pgvector Embeddings)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS furniture_catalog_items (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    width_m NUMERIC(6, 3) NOT NULL,
    height_m NUMERIC(6, 3) NOT NULL,
    clearance_json JSONB NOT NULL DEFAULT '{"front": 0.8, "back": 0.5, "sides": 0.2}'::jsonb,
    aliases JSONB DEFAULT '[]'::jsonb,
    embedding VECTOR(1536), -- Vector embeddings for semantic search
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 5. Requirements & Clarifications
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requirement_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
    region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    spec_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clarification_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_sets(id) ON DELETE CASCADE,
    question_json JSONB NOT NULL,
    user_answer TEXT,
    is_blocking BOOLEAN DEFAULT TRUE,
    answered_at TIMESTAMPTZ
);

-- -----------------------------------------------------------------------------
-- 6. Layout Proposals, Revisions & Patches
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS layout_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
    region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
    strategy_name VARCHAR(255) NOT NULL,
    score NUMERIC(5, 2) DEFAULT 0.0,
    placed_objects_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS revisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
    base_revision_id UUID REFERENCES revisions(id),
    version_no INT NOT NULL,
    operations_json JSONB NOT NULL DEFAULT '[]'::jsonb, -- Append-only layout patch operations
    snapshot_json JSONB, -- Periodic full snapshot cache
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 7. Validation & Approvals Workflow
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    revision_id UUID REFERENCES revisions(id) ON DELETE CASCADE,
    suggestion_id UUID REFERENCES layout_suggestions(id) ON DELETE CASCADE,
    is_valid BOOLEAN NOT NULL,
    violations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
    revision_id UUID NOT NULL REFERENCES revisions(id),
    stage VARCHAR(50) NOT NULL CHECK (stage IN ('DRAFT', 'SALES_REVIEW', 'LAYOUT_EXEC_REVIEW', 'LAYOUT_MGR_REVIEW', 'FINAL_APPROVED')),
    decision VARCHAR(50) NOT NULL CHECK (decision IN ('SUBMIT', 'APPROVE', 'REJECT', 'REVOKE')),
    comment TEXT,
    actor_id UUID NOT NULL REFERENCES users(id),
    content_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of immutable snapshot
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    entity_ref VARCHAR(255) NOT NULL,
    details_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 8. Spatial, GIN & B-Tree Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_regions_geom ON regions USING GIST (polygon_geom);
CREATE INDEX IF NOT EXISTS idx_req_spec_json ON requirement_sets USING GIN (spec_json);
CREATE INDEX IF NOT EXISTS idx_rev_ops_json ON revisions USING GIN (operations_json);
CREATE INDEX IF NOT EXISTS idx_suggestions_floor_plan ON layout_suggestions(floor_plan_id);
CREATE INDEX IF NOT EXISTS idx_approvals_revision ON approvals(revision_id);
CREATE INDEX IF NOT EXISTS idx_catalog_category ON furniture_catalog_items(category);
