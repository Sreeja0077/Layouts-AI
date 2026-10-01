"""
Authentication dependencies and JWT token validation.
Extracts authenticated user context (user_id, email, role, org_id) from HTTP Bearer tokens or dev mock auth.
Cryptographically verifies JWT signatures using PyJWT or standard Python HMAC-SHA256 cryptography.
"""

import base64
import hashlib
import hmac
import json
from enum import Enum
from typing import Any, Dict, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from app.security.config import security_settings

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    jwt = None
    HAS_PYJWT = False

security_bearer = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    SALES_EXEC = "SALES_EXEC"
    LAYOUT_EXEC = "LAYOUT_EXEC"
    LAYOUT_MGR = "LAYOUT_MGR"
    SALES_MGR = "SALES_MGR"
    ADMIN = "ADMIN"


class AuthenticatedUser(BaseModel):
    """Authenticated user context object."""
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="Unique user ID")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(..., description="Assigned system role")
    org_id: str = Field(..., description="Organization ID for multi-tenant isolation")


def _base64_url_decode(data: str) -> bytes:
    """Helper for base64url decoding with padding."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_signed_jwt(payload: Dict[str, Any], secret_key: str, algorithm: str = "HS256") -> str:
    """Generate a cryptographically signed HS256 JWT token for testing/issuance."""
    if HAS_PYJWT and jwt is not None:
        return jwt.encode(payload, secret_key, algorithm=algorithm)

    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_bytes = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature_bytes).decode("utf-8").rstrip("=")

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_and_verify_jwt(token: str, secret_key: str, algorithm: str = "HS256") -> Dict[str, Any]:
    """
    Cryptographically verify and decode a JWT token.
    Uses PyJWT if available or standard library HMAC-SHA256 signature verification.
    """
    if HAS_PYJWT and jwt is not None:
        try:
            return jwt.decode(token, secret_key, algorithms=[algorithm], options={"verify_aud": False})
        except Exception as exc:
            raise ValueError(f"JWT verification failed: {str(exc)}")

    # Standard library HMAC-SHA256 signature verification
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: expected 3 dot-separated components")

    header_b64, payload_b64, signature_b64 = parts[0], parts[1], parts[2]

    # 1. Decode header and verify algorithm
    try:
        header_bytes = _base64_url_decode(header_b64)
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid JWT header encoding")

    if header.get("alg") != algorithm:
        raise ValueError(f"Invalid JWT algorithm: expected '{algorithm}', got '{header.get('alg')}'")

    # 2. Cryptographically verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig_bytes = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        received_sig_bytes = _base64_url_decode(signature_b64)
    except Exception:
        raise ValueError("Invalid signature encoding")

    if not hmac.compare_digest(expected_sig_bytes, received_sig_bytes):
        raise ValueError("Invalid JWT signature: cryptographic verification failed")

    # 3. Decode and parse payload
    try:
        payload_bytes = _base64_url_decode(payload_b64)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid JWT payload encoding")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> AuthenticatedUser:
    """
    FastAPI Dependency: Authenticates incoming request using JWT Bearer token or Dev Mock Auth.
    """
    if credentials is None:
        if security_settings.ALLOW_MOCK_AUTH:
            return AuthenticatedUser(
                user_id="usr_mock_001",
                email="dev_user@company.com",
                role=UserRole.LAYOUT_EXEC,
                org_id="org_mock_999",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_and_verify_jwt(
            token,
            security_settings.JWT_SECRET_KEY,
            security_settings.JWT_ALGORITHM,
        )

        role_str = payload.get("role")
        try:
            role_enum = UserRole(role_str)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid user role '{role_str}' in token payload")

        return AuthenticatedUser(
            user_id=payload.get("sub", payload.get("user_id", "usr_unknown")),
            email=payload.get("email", "unknown@company.com"),
            role=role_enum,
            org_id=payload.get("org_id", "org_default"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
