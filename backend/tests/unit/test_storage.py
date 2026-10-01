"""
Unit test for Object Storage client integration (Task 1.4).
Verifies file upload, byte retrieval, presigned URL generation, and file deletion.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.integrations.storage import ObjectStorageClient


def test_object_storage_lifecycle():
    client = ObjectStorageClient(bucket_name="test-bucket")
    test_key = "floor_plans/test_blueprint_v1.dxf"
    test_content = b"HEADER_DXF_CAD_DATA_V1_STREAM"

    # 1. Test Upload
    location = client.upload_file(test_content, test_key)
    assert location == f"test-bucket/{test_key}"

    # 2. Test Retrieval
    retrieved_content = client.get_file(test_key)
    assert retrieved_content == test_content

    # 3. Test Presigned URL
    url = client.get_presigned_url(test_key, expires_in_seconds=1800)
    assert "test-bucket" in url
    assert test_key in url

    # 4. Test Delete
    deleted = client.delete_file(test_key)
    assert deleted is True

    print("ALL OBJECT STORAGE INTEGRATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_object_storage_lifecycle()
