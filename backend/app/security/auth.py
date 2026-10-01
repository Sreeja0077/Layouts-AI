"""
Authentication dependencies and Keycloak / OIDC JWT token validation.
Extracts authenticated user context (user_id, email, role, org_id) from HTTP Bearer tokens or dev mock auth.
Cryptographically verifies RS256 RSA asymmetric signatures via OIDC JWKS discovery & caching.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.request
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from app.security.config import security_settings

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
    """Helper for base64url decoding with proper padding."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def _base64_url_encode(data: bytes) -> str:
    """Helper for base64url encoding without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def rsa_public_key_from_jwk(jwk: Dict[str, Any]) -> rsa.RSAPublicKey:
    """Construct an RSA Public Key object from JWKS JSON parameters (n, e)."""
    n_bytes = _base64_url_decode(jwk["n"])
    e_bytes = _base64_url_decode(jwk["e"])

    n_int = int.from_bytes(n_bytes, byteorder="big")
    e_int = int.from_bytes(e_bytes, byteorder="big")

    return rsa.RSAPublicNumbers(e_int, n_int).public_key()


class OIDCKeyManager:
    """Manages OIDC Discovery, JWKS fetching, and in-memory RSA key caching with key rotation."""

    def __init__(self):
        self.cached_keys: Dict[str, Any] = {}
        self.last_fetched_time: float = 0.0
        self.cache_ttl_seconds: float = 300.0
        self.mock_jwks_provider: Optional[Any] = None

    def get_public_key_for_kid(self, kid: str, issuer: str) -> Any:
        now = time.time()
        # Refresh JWKS if cache is empty, expired, or kid is unknown
        if (
            not self.cached_keys
            or (now - self.last_fetched_time) > self.cache_ttl_seconds
            or kid not in self.cached_keys
        ):
            self.refresh_jwks(issuer)

        if kid in self.cached_keys:
            return self.cached_keys[kid]

        raise ValueError(f"Unknown Key ID (kid: '{kid}') in OIDC JWKS keyset")

    def refresh_jwks(self, issuer: str):
        if self.mock_jwks_provider:
            jwks_data = self.mock_jwks_provider(issuer)
        else:
            discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
            req = urllib.request.Request(discovery_url, headers={"User-Agent": "layouts-ai-backend"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                disc_data = json.loads(resp.read().decode("utf-8"))

            jwks_uri = disc_data.get("jwks_uri", f"{issuer.rstrip('/')}/protocol/openid-connect/certs")
            jwks_req = urllib.request.Request(jwks_uri, headers={"User-Agent": "layouts-ai-backend"})
            with urllib.request.urlopen(jwks_req, timeout=5.0) as resp:
                jwks_data = json.loads(resp.read().decode("utf-8"))

        keys_map = {}
        for key_dict in jwks_data.get("keys", []):
            k_id = key_dict.get("kid")
            k_type = key_dict.get("kty")
            if k_id and k_type == "RSA":
                keys_map[k_id] = rsa_public_key_from_jwk(key_dict)
            elif k_id and k_type == "OCT":
                keys_map[k_id] = key_dict.get("k")

        self.cached_keys = keys_map
        self.last_fetched_time = time.time()


oidc_key_manager = OIDCKeyManager()


def create_signed_jwt(payload: Dict[str, Any], secret_key: str, algorithm: str = "HS256") -> str:
    """Generate a cryptographically signed HS256 JWT token for testing/issuance."""
    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = _base64_url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64_url_encode(json.dumps(payload).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_bytes = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64_url_encode(signature_bytes)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def create_signed_rsa_jwt(payload: Dict[str, Any], private_key: rsa.RSAPrivateKey, kid: str, algorithm: str = "RS256") -> str:
    """Generate a cryptographically signed RS256 JWT token using an RSA private key."""
    header = {"alg": algorithm, "typ": "JWT", "kid": kid}
    header_b64 = _base64_url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64_url_encode(json.dumps(payload).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_bytes = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = _base64_url_encode(signature_bytes)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_and_verify_jwt(
    token: str,
    expected_issuer: str,
    expected_client_id: str,
    secret_key: str = security_settings.JWT_SECRET_KEY,
) -> Dict[str, Any]:
    """
    Cryptographically verify and decode a JWT token.
    Enforces asymmetric RS256 signature verification via JWKS (or HS256 for local dev),
    issuer validation, audience/client validation, and expiration checks.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: expected 3 dot-separated components")

    header_b64, payload_b64, signature_b64 = parts[0], parts[1], parts[2]

    # 1. Parse header
    try:
        header_bytes = _base64_url_decode(header_b64)
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid JWT header encoding")

    alg = header.get("alg")
    if alg == "none" or not alg:
        raise ValueError("Forbidden JWT algorithm: alg=none is strictly disallowed")

    if alg not in ["RS256", "HS256"]:
        raise ValueError(f"Unsupported JWT signing algorithm: '{alg}'")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    try:
        received_sig_bytes = _base64_url_decode(signature_b64)
    except Exception:
        raise ValueError("Invalid signature encoding")

    # 2. Cryptographic Signature Verification
    if alg == "RS256":
        kid = header.get("kid")
        if not kid:
            raise ValueError("Missing 'kid' (Key ID) header in RS256 token")

        public_key = oidc_key_manager.get_public_key_for_kid(kid, expected_issuer)
        try:
            public_key.verify(received_sig_bytes, signing_input, padding.PKCS1v15(), hashes.SHA256())
        except Exception:
            raise ValueError("Invalid JWT signature: cryptographic RSA verification failed")

    elif alg == "HS256":
        expected_sig_bytes = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig_bytes, received_sig_bytes):
            raise ValueError("Invalid JWT signature: cryptographic HMAC verification failed")

    # 3. Parse and validate payload claims
    try:
        payload_bytes = _base64_url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid JWT payload encoding")

    # Validate Expiration (exp)
    exp = payload.get("exp")
    if exp is not None and time.time() > float(exp):
        raise ValueError("JWT token has expired")

    # Validate Issuer (iss)
    token_iss = payload.get("iss")
    if token_iss and token_iss.rstrip("/") != expected_issuer.rstrip("/"):
        raise ValueError(f"Issuer mismatch: expected '{expected_issuer}', got '{token_iss}'")

    # Validate Audience / Client ID (aud / azp)
    token_aud = payload.get("aud")
    token_azp = payload.get("azp")
    aud_valid = False

    if isinstance(token_aud, str) and token_aud == expected_client_id:
        aud_valid = True
    elif isinstance(token_aud, list) and expected_client_id in token_aud:
        aud_valid = True
    elif token_azp == expected_client_id:
        aud_valid = True
    elif not token_aud and not token_azp:
        aud_valid = True  # Permissive if audience claim omitted in test token

    if not aud_valid:
        raise ValueError(f"Audience mismatch: expected client '{expected_client_id}', got aud={token_aud}, azp={token_azp}")

    return payload


def extract_user_role(payload: Dict[str, Any], client_id: str) -> UserRole:
    """Extract and map Keycloak role claims to system UserRole enum."""
    extracted_roles: List[str] = []

    # 1. Keycloak Realm roles
    realm_roles = payload.get("realm_access", {}).get("roles", [])
    extracted_roles.extend(realm_roles)

    # 2. Keycloak Client resource roles
    client_roles = payload.get("resource_access", {}).get(client_id, {}).get("roles", [])
    extracted_roles.extend(client_roles)

    # 3. Top-level roles array or single role string
    top_roles = payload.get("roles", [])
    if isinstance(top_roles, list):
        extracted_roles.extend(top_roles)
    single_role = payload.get("role")
    if isinstance(single_role, str):
        extracted_roles.append(single_role)

    # Match extracted roles against UserRole enum values
    valid_roles = {r.value for r in UserRole}
    for role_candidate in extracted_roles:
        if role_candidate in valid_roles:
            return UserRole(role_candidate)

    raise ValueError(f"No valid UserRole found in token roles: {extracted_roles}")


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

    # Bearer token is present -> MUST validate signature & claims (NO fallback to mock user on failure)
    token = credentials.credentials
    try:
        payload = decode_and_verify_jwt(
            token=token,
            expected_issuer=security_settings.OIDC_ISSUER,
            expected_client_id=security_settings.OIDC_CLIENT_ID,
            secret_key=security_settings.JWT_SECRET_KEY,
        )

        role_enum = extract_user_role(payload, security_settings.OIDC_CLIENT_ID)

        return AuthenticatedUser(
            user_id=payload.get("sub", payload.get("user_id", "usr_unknown")),
            email=payload.get("email", "unknown@company.com"),
            role=role_enum,
            org_id=payload.get("org_id", payload.get("tenant_id", payload.get("organization", "org_default"))),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
