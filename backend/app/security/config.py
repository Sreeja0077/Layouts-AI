"""
Security and authentication configuration settings.
Supports OIDC / Keycloak RSA JWT validation and local development mock authentication.
"""

import os
from pydantic import BaseModel, ConfigDict, Field


class SecuritySettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    OIDC_ISSUER: str = Field(
        default_factory=lambda: os.getenv(
            "OIDC_ISSUER", os.getenv("KEYCLOAK_URL", "http://localhost:8080/realms/layouts-ai")
        )
    )
    OIDC_CLIENT_ID: str = Field(
        default_factory=lambda: os.getenv(
            "OIDC_CLIENT_ID", os.getenv("KEYCLOAK_CLIENT_ID", "layouts-ai-backend")
        )
    )

    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "dev_super_secret_jwt_key_32bytes_min")
    )
    JWT_ALGORITHM: str = Field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "RS256")
    )

    # Local development bypass flag (allows mock header authentication during testing when no Bearer header is present)
    ALLOW_MOCK_AUTH: bool = Field(
        default_factory=lambda: os.getenv("ALLOW_MOCK_AUTH", "true").lower() == "true"
    )

    # Backwards-compatible aliases
    @property
    def KEYCLOAK_URL(self) -> str:
        return self.OIDC_ISSUER

    @property
    def KEYCLOAK_CLIENT_ID(self) -> str:
        return self.OIDC_CLIENT_ID


security_settings = SecuritySettings()
