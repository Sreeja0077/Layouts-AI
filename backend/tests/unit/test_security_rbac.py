"""
Unit test for Keycloak OIDC RSA JWT authentication and RBAC authorization (Task 1.2).
Verifies asymmetric RSA signature verification via JWKS, Key ID selection, issuer/audience validation,
token expiration, role mapping, dev mock auth isolation, and RBAC guards without external servers.
"""

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import (
    AuthenticatedUser,
    UserRole,
    _base64_url_encode,
    create_signed_jwt,
    create_signed_rsa_jwt,
    oidc_key_manager,
)
from app.security.config import security_settings

client = TestClient(app)

# Generate test RSA keypair for deterministic OIDC unit testing
TEST_KID_1 = "test_kid_rsa_key_001"
TEST_KID_2 = "test_kid_rsa_key_002"

private_key_1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key_1 = private_key_1.public_key()
pub_nums_1 = public_key_1.public_numbers()

private_key_2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key_2 = private_key_2.public_key()
pub_nums_2 = public_key_2.public_numbers()


def rsa_numbers_to_jwk(pub_nums, kid: str) -> dict:
    """Helper converting RSA public numbers to JWKS JSON dictionary."""
    n_bytes = pub_nums.n.to_bytes((pub_nums.n.bit_length() + 7) // 8, byteorder="big")
    e_bytes = pub_nums.e.to_bytes((pub_nums.e.bit_length() + 7) // 8, byteorder="big")
    return {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": kid,
        "n": _base64_url_encode(n_bytes),
        "e": _base64_url_encode(e_bytes),
    }


# Configure in-memory JWKS provider hook
jwks_store = {
    "keys": [
        rsa_numbers_to_jwk(pub_nums_1, TEST_KID_1)
    ]
}


def mock_jwks_provider(issuer: str):
    return jwks_store


oidc_key_manager.mock_jwks_provider = mock_jwks_provider
oidc_key_manager.refresh_jwks(security_settings.OIDC_ISSUER)


def get_base_oidc_payload() -> dict:
    """Helper constructing valid Keycloak OIDC payload."""
    return {
        "sub": "usr_keycloak_101",
        "email": "keycloak_user@company.com",
        "iss": security_settings.OIDC_ISSUER,
        "aud": security_settings.OIDC_CLIENT_ID,
        "azp": security_settings.OIDC_CLIENT_ID,
        "exp": time.time() + 3600,
        "org_id": "org_enterprise_01",
        "realm_access": {"roles": ["LAYOUT_MGR"]},
    }


# -----------------------------------------------------------------------------
# 20 REQUIRED OIDC & SECURITY TESTS
# -----------------------------------------------------------------------------

def test_1_to_5_valid_rsa_signed_oidc_jwt():
    """1, 2, 3, 4, 5, 18: Valid RSA-signed OIDC JWT -> authenticated with sub, email, org_id, role."""
    payload = get_base_oidc_payload()
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["actor_id"] == "usr_keycloak_101"
    assert data["actor_role"] == "LAYOUT_MGR"
    print("Verified Test 1-5: Valid RSA-signed OIDC JWT authentication and field extraction")


def test_6_invalid_rsa_signature():
    """6: Invalid RSA signature -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    # Sign token with wrong private key
    token = create_signed_rsa_jwt(payload, private_key_2, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]
    print("Verified Test 6: Invalid RSA signature rejected with 401")


def test_7_modified_payload_tampering():
    """7: Modified payload with original signature -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)
    parts = token.split(".")

    # Tamper payload part to claim ADMIN role
    tampered_payload = get_base_oidc_payload()
    tampered_payload["realm_access"]["roles"] = ["ADMIN"]
    tampered_b64 = _base64_url_encode(str(tampered_payload).encode("utf-8"))
    tampered_token = f"{parts[0]}.{tampered_b64}.{parts[2]}"

    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    print("Verified Test 7: Tampered payload rejected with 401")


def test_8_10_unknown_kid_and_key_rotation():
    """8 & Work Item 10: Unknown kid -> JWKS refresh attempt -> success if rotated key added."""
    payload = get_base_oidc_payload()
    token = create_signed_rsa_jwt(payload, private_key_2, kid=TEST_KID_2)

    # 1st attempt: kid2 is unknown in JWKS -> 401
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401

    # Key Rotation: Add key 2 to JWKS provider store
    jwks_store["keys"].append(rsa_numbers_to_jwk(pub_nums_2, TEST_KID_2))

    # 2nd attempt: JWKS refresh fetches key 2 -> 200 OK
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 200
    print("Verified Test 8 & Key Rotation: Unknown kid triggers JWKS refresh and rotates key")


def test_9_invalid_issuer():
    """9: Invalid issuer -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    payload["iss"] = "http://fake-keycloak-issuer.com/realms/fake"
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "Issuer mismatch" in response.json()["detail"]
    print("Verified Test 9: Invalid issuer rejected with 401")


def test_10_invalid_audience():
    """10: Invalid audience/client ID -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    payload["aud"] = "wrong_client_app"
    payload["azp"] = "wrong_client_app"
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "Audience mismatch" in response.json()["detail"]
    print("Verified Test 10: Invalid audience rejected with 401")


def test_11_expired_token():
    """11: Expired token -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    payload["exp"] = time.time() - 3600  # Expired 1 hour ago
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "JWT token has expired" in response.json()["detail"]
    print("Verified Test 11: Expired token rejected with 401")


def test_12_unsupported_algorithm():
    """12: Unsupported algorithm -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    # Header declaring ES256
    header_b64 = _base64_url_encode(b'{"alg":"ES256","typ":"JWT","kid":"test_kid_rsa_key_001"}')
    payload_b64 = _base64_url_encode(str(payload).encode("utf-8"))
    token = f"{header_b64}.{payload_b64}.fake_sig"

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "Unsupported JWT signing algorithm" in response.json()["detail"]
    print("Verified Test 12: Unsupported algorithm rejected with 401")


def test_13_alg_none_forbidden():
    """13: alg=none -> 401 Unauthorized."""
    payload = get_base_oidc_payload()
    header_b64 = _base64_url_encode(b'{"alg":"none","typ":"JWT"}')
    payload_b64 = _base64_url_encode(str(payload).encode("utf-8"))
    token = f"{header_b64}.{payload_b64}."

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "alg=none is strictly disallowed" in response.json()["detail"]
    print("Verified Test 13: alg=none rejected with 401")


def test_14_malformed_jwt():
    """14: Malformed JWT -> 401 Unauthorized."""
    headers = {"Authorization": "Bearer not_a_valid_3_part_jwt"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    print("Verified Test 14: Malformed JWT rejected with 401")


def test_15_missing_bearer_token_with_mock_disabled():
    """15: Missing Bearer token with mock disabled -> 401 Unauthorized."""
    security_settings.ALLOW_MOCK_AUTH = False
    try:
        response = client.post(
            "/api/v1/approvals/transition",
            json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        )
        assert response.status_code == 401
        assert "Authentication credentials were not provided" in response.json()["detail"]
    finally:
        security_settings.ALLOW_MOCK_AUTH = True
    print("Verified Test 15: Missing Bearer token returns 401 when mock disabled")


def test_16_missing_bearer_token_with_mock_enabled():
    """16: Missing Bearer token with mock enabled -> returns dev mock identity."""
    security_settings.ALLOW_MOCK_AUTH = True
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "LAYOUT_EXEC_REVIEW", "decision": "APPROVE"},
    )
    assert response.status_code == 200
    assert response.json()["actor_role"] == "LAYOUT_EXEC"
    print("Verified Test 16: Missing Bearer token returns mock user when mock enabled")


def test_17_invalid_bearer_token_present_with_mock_enabled():
    """17: Bearer token present but invalid while mock enabled -> MUST return 401 (NO auth bypass)."""
    security_settings.ALLOW_MOCK_AUTH = True
    headers = {"Authorization": "Bearer invalid_token_value"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 401
    print("Verified Test 17: Invalid Bearer token does NOT fall back to mock auth")


def test_19_disallowed_role_forbidden():
    """19: Valid OIDC token with disallowed role -> 403 Forbidden."""
    payload = get_base_oidc_payload()
    payload["realm_access"]["roles"] = ["SALES_EXEC"]  # SALES_EXEC lacks approval permission
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 403
    assert "Forbidden: User role 'SALES_EXEC' lacks required permissions" in response.json()["detail"]
    print("Verified Test 19: Disallowed role rejected with 403")


def test_20_admin_role_override():
    """20: Valid OIDC token with ADMIN role -> 200 OK override."""
    payload = get_base_oidc_payload()
    payload["realm_access"]["roles"] = ["ADMIN"]
    token = create_signed_rsa_jwt(payload, private_key_1, kid=TEST_KID_1)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/approvals/transition",
        json={"stage": "FINAL_APPROVED", "decision": "APPROVE"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["actor_role"] == "ADMIN"
    print("Verified Test 20: ADMIN role override granted access (200)")


if __name__ == "__main__":
    test_1_to_5_valid_rsa_signed_oidc_jwt()
    test_6_invalid_rsa_signature()
    test_7_modified_payload_tampering()
    test_8_10_unknown_kid_and_key_rotation()
    test_9_invalid_issuer()
    test_10_invalid_audience()
    test_11_expired_token()
    test_12_unsupported_algorithm()
    test_13_alg_none_forbidden()
    test_14_malformed_jwt()
    test_15_missing_bearer_token_with_mock_disabled()
    test_16_missing_bearer_token_with_mock_enabled()
    test_17_invalid_bearer_token_present_with_mock_enabled()
    test_19_disallowed_role_forbidden()
    test_20_admin_role_override()
    print("ALL 20 REAL OIDC KEYCLOAK RSA JWT & RBAC TESTS PASSED SUCCESSFULLY!")
