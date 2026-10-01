"""
Security and authentication configuration settings.
Supports Keycloak OIDC JWT token validation and local development mock authentication.
Uses standard Pydantic BaseModel and os.getenv to avoid pydantic-settings dependency issues.
"""

import os
from pydantic import BaseModel, ConfigDict, Field


class SecuritySettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "dev_super_secret_jwt_key_32bytes_min")
    )
    JWT_ALGORITHM: str = Field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )
    KEYCLOAK_URL: str = Field(
        default_factory=lambda: os.getenv("KEYCLOAK_URL", "http://localhost:8080/realms/layouts-ai")
    )
    KEYCLOAK_CLIENT_ID: str = Field(
        default_factory=lambda: os.getenv("KEYCLOAK_CLIENT_ID", "layouts-ai-backend")
    )

    # Local development bypass flag (allows mock header authentication during testing)
    ALLOW_MOCK_AUTH: bool = Field(
        default_factory=lambda: os.getenv("ALLOW_MOCK_AUTH", "true").lower() == "true"
    )


security_settings = SecuritySettings()
