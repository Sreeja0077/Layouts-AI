"""
Unit test for security authentication and RBAC authorization (Task 1.2).
Verifies cryptographic JWT token verification, signature validation, dev mock auth toggle, and role permission guards.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.security.auth import AuthenticatedUser, UserRole, create_signed_jwt
from app.security.config import security_settings

client = TestClient(app)


def test_mock_dev_auth_enabled():
    """7: Verify endpoint access using local dev mock auth when ALLOW_MOCK_AUTH is enabled."""
    security_settings.ALLOW_MOCK_AUTH = True
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "LAYOUT_EXEC_REVIEW", "decision": "APPROVE"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RECORDED"
    assert data["actor_role"] == "LAYOUT_EXEC"


def test_missing_bearer_token_unauthorized_when_mock_disabled():
    """6 & 13: Verify 401 Unauthorized when Bearer token is missing and ALLOW_MOCK_AUTH is disabled."""
    security_settings.ALLOW_MOCK_AUTH = False
    try:
        response = client.post(
            "/api/v1/approvals/transition",
            json={"stage": "LAYOUT_EXEC_REVIEW", "decision": "APPROVE"},
        )
        assert response.status_code == 401
        assert "Authentication credentials were not provided" in response.json()["detail"]
    finally:
        security_settings.ALLOW_MOCK_AUTH = True


def test_jwt_token_auth_success_and_field_extraction():
    """1, 2, 8, 11, 12, 14: Verify valid signed JWT token authentication and claim extraction."""
    payload = {
        "sub": "usr_sales_101",
        "email": "sales_mgr@company.com",
        "role": "SALES_MGR",
        "org_id": "org_777",
    }
    valid_token = create_signed_jwt(payload, security_settings.JWT_SECRET_KEY, security_settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["actor_id"] == "usr_sales_101"
    assert data["actor_role"] == "SALES_MGR"


def test_admin_role_override_success():
    """10: Verify ADMIN role bypasses specific role restrictions and gains access."""
    payload = {
        "sub": "usr_admin_001",
        "email": "admin@company.com",
        "role": "ADMIN",
        "org_id": "org_root",
    }
    admin_token = create_signed_jwt(payload, security_settings.JWT_SECRET_KEY, security_settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "LAYOUT_MGR_REVIEW", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["actor_role"] == "ADMIN"


def test_invalid_signature_token_rejected():
    """3 & 15: Verify 401 Unauthorized when JWT token signature is tampered or fake."""
    payload = {
        "sub": "usr_hacker",
        "email": "hacker@company.com",
        "role": "ADMIN",
        "org_id": "org_fake",
    }
    # Create token with wrong secret key
    bad_sig_token = create_signed_jwt(payload, "wrong_secret_key_xxxxxxxxx", security_settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {bad_sig_token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_fake_mock_signature_rejected():
    """3 & 15: Verify fake signature string 'mock_sig_123' is rejected with 401."""
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfZmFrZSIsInJvbGUiOiJBRE1JTiJ9.mock_sig_123"
    headers = {"Authorization": f"Bearer {fake_token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401


def test_malformed_token_rejected():
    """4: Verify 401 Unauthorized for malformed non-JWT header strings."""
    headers = {"Authorization": "Bearer not_a_valid_jwt_token"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401


def test_invalid_role_value_rejected():
    """5: Verify 401 Unauthorized when JWT token contains unknown/invalid role."""
    payload = {
        "sub": "usr_bad_role",
        "email": "user@company.com",
        "role": "INVALID_ROLE_TYPE",
        "org_id": "org_777",
    }
    token = create_signed_jwt(payload, security_settings.JWT_SECRET_KEY, security_settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "LAYOUT_MGR_REVIEW", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401


def test_disallowed_role_forbidden_access():
    """9 & 14: Verify 403 Forbidden rejection when role lacks required permissions."""
    # SALES_EXEC is not in [LAYOUT_EXEC, LAYOUT_MGR, SALES_MGR]
    payload = {
        "sub": "usr_exec_001",
        "email": "sales_exec@company.com",
        "role": "SALES_EXEC",
        "org_id": "org_777",
    }
    token = create_signed_jwt(payload, security_settings.JWT_SECRET_KEY, security_settings.JWT_ALGORITHM)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "LAYOUT_MGR_REVIEW", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 403
    assert "Forbidden: User role 'SALES_EXEC' lacks required permissions" in response.json()["detail"]


if __name__ == "__main__":
    test_mock_dev_auth_enabled()
    test_missing_bearer_token_unauthorized_when_mock_disabled()
    test_jwt_token_auth_success_and_field_extraction()
    test_admin_role_override_success()
    test_invalid_signature_token_rejected()
    test_fake_mock_signature_rejected()
    test_malformed_token_rejected()
    test_invalid_role_value_rejected()
    test_disallowed_role_forbidden_access()
    print("ALL SECURITY & RBAC AUTHORIZATION TESTS PASSED SUCCESSFULLY!")
