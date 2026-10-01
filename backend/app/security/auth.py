"""
Authentication dependencies and JWT token validation.
Extracts user identity (user_id, email, role, org_id) from HTTP Bearer tokens or mock headers.
Supports PyJWT with a built-in base64 JSON decoder fallback.
"""

import base64
import json
from enum import Enum
from typing import Dict, Any, List, Optional
from fastapi import Depends, HTTPException, Security, status
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


def decode_jwt_payload(token: str, secret_key: str, algorithm: str) -> Dict[str, Any]:
    """Decode JWT token using PyJWT or fallback base64 JSON decoder."""
    if HAS_PYJWT and jwt is not None:
        return jwt.decode(token, secret_key, algorithms=[algorithm], options={"verify_aud": False})

    # Fallback for environments where PyJWT is not yet installed
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format (expected 3 dot-separated parts)")
        payload_b64 = parts[1]
        # Pad base64 string if needed
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to decode token payload: {str(exc)}")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> AuthenticatedUser:
    """
    FastAPI Dependency: Authenticates incoming request using JWT Bearer token or Dev Mock Auth.
    """
    if credentials is None:
        if security_settings.ALLOW_MOCK_AUTH:
            # Fallback mock user for dev/testing when no token is supplied
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
        payload = decode_jwt_payload(
            token,
            security_settings.JWT_SECRET_KEY,
            security_settings.JWT_ALGORITHM,
        )
        return AuthenticatedUser(
            user_id=payload.get("sub", payload.get("user_id", "usr_unknown")),
            email=payload.get("email", "unknown@company.com"),
            role=UserRole(payload.get("role", "SALES_EXEC")),
            org_id=payload.get("org_id", "org_default"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
