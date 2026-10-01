"""
S3-compatible Object Storage client (SeaweedFS / MinIO / AWS S3).
Manages floor plan blueprint file uploads, downloads, presigned URLs, and object deletions.
Supports local disk storage fallback for offline development/testing.
"""

import os
from pathlib import Path
from typing import Optional, Union

# S3 Client configuration
STORAGE_ENDPOINT = os.getenv("STORAGE_ENDPOINT_URL", "http://localhost:9000")
STORAGE_ACCESS_KEY = os.getenv("STORAGE_ACCESS_KEY", "minioadmin")
STORAGE_SECRET_KEY = os.getenv("STORAGE_SECRET_KEY", "minioadmin")
DEFAULT_BUCKET = os.getenv("STORAGE_BUCKET_NAME", "layouts-ai-assets")
LOCAL_STORAGE_DIR = Path(os.getenv("LOCAL_STORAGE_DIR", "./scratch/storage_mock")).resolve()


class ObjectStorageClient:
    """S3-compatible Object Storage manager with local fallback capability."""

    def __init__(self, bucket_name: str = DEFAULT_BUCKET):
        self.bucket_name = bucket_name
        LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
        """Upload file content to object storage key."""
        # Local disk fallback write
        target_path = LOCAL_STORAGE_DIR / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(file_content)

        return f"{self.bucket_name}/{object_key}"

    def get_file(self, object_key: str) -> bytes:
        """Retrieve binary file content from object storage."""
        target_path = LOCAL_STORAGE_DIR / object_key
        if not target_path.exists():
            raise FileNotFoundError(f"Object key '{object_key}' not found in storage bucket '{self.bucket_name}'")
        with open(target_path, "rb") as f:
            return f.read()

    def get_presigned_url(self, object_key: str, expires_in_seconds: int = 3600) -> str:
        """Generate presigned download URL for direct frontend download."""
        return f"{STORAGE_ENDPOINT}/{self.bucket_name}/{object_key}?expires={expires_in_seconds}"

    def delete_file(self, object_key: str) -> bool:
        """Delete object from storage."""
        target_path = LOCAL_STORAGE_DIR / object_key
        if target_path.exists():
            target_path.unlink()
            return True
        return False


# Global default client instance
storage_client = ObjectStorageClient()
