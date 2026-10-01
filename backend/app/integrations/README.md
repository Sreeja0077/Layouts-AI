# Integrations Module

## 📌 Purpose & Overview
Manages external service clients (Object Storage, LLM gateway, email/notification dispatchers).

## 🏗️ Architectural Role
- **Domain Layer:** `backend/app/integrations`
- **System Authority:** External API abstraction layer; decouples core application code from specific vendor implementations.

## 📁 Files & Responsibilities
- [`storage.py`](file:///d:/Layouts%20AI/backend/app/integrations/storage.py): Object Storage client interface (`ObjectStorageClient`, `storage_client`).
  - **Why needed:** Provides S3/MinIO/SeaweedFS file storage for uploaded BIM IFC files, 2D CAD DXF drawings, PDF blueprints, and floor plan images, with local disk fallback for dev testing.

## 🔒 Security & Quality Invariants
- Direct database binary storage is forbidden; all heavy files must pass through Object Storage.
- Presigned URLs are time-limited to prevent unauthorized file access.

---
*Maintained continuously across development tasks.*
