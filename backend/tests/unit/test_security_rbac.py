"""
Unit test for security authentication and RBAC authorization (Task 1.2).
Verifies JWT token decoding, dev mock user fallback, and role permission guards.
"""

import base64
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.security import AuthenticatedUser, UserRole, security_settings

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    jwt = None
    HAS_PYJWT = False

client = TestClient(app)


def encode_test_token(payload: dict) -> str:
    """Helper to encode a JWT token for testing, using PyJWT or base64 JSON encoder."""
    if HAS_PYJWT and jwt is not None:
        return jwt.encode(payload, security_settings.JWT_SECRET_KEY, algorithm=security_settings.JWT_ALGORITHM)

    # Base64 fallback encoding when PyJWT is not installed
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = "mock_sig_123"
    return f"{header_b64}.{payload_b64}.{signature}"


def test_mock_dev_auth_access():
    """Verify endpoint access using local dev mock authentication."""
    response = client.post("/api/v1/approvals/transition", json={"stage": "LAYOUT_EXEC_REVIEW", "decision": "APPROVE"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RECORDED"
    assert data["actor_role"] == "LAYOUT_EXEC"


def test_jwt_token_auth_success():
    """Verify endpoint access with a valid signed JWT token."""
    token_payload = {
        "sub": "usr_sales_101",
        "email": "sales_mgr@company.com",
        "role": "SALES_MGR",
        "org_id": "org_777",
    }
    token = encode_test_token(token_payload)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["actor_id"] == "usr_sales_101"
    assert data["actor_role"] == "SALES_MGR"


def test_jwt_role_forbidden_access():
    """Verify 403 Forbidden rejection when role lacks required permission."""
    # SALES_EXEC is not in [LAYOUT_EXEC, LAYOUT_MGR, SALES_MGR]
    token_payload = {
        "sub": "usr_exec_001",
        "email": "sales_exec@company.com",
        "role": "SALES_EXEC",
        "org_id": "org_777",
    }
    token = encode_test_token(token_payload)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "LAYOUT_MGR_REVIEW", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 403
    assert "Forbidden: User role 'SALES_EXEC' lacks required permissions" in response.json()["detail"]


if __name__ == "__main__":
    test_mock_dev_auth_access()
    test_jwt_token_auth_success()
    test_jwt_role_forbidden_access()
    print("ALL SECURITY & RBAC AUTHORIZATION TESTS PASSED SUCCESSFULLY!")
