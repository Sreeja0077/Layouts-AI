"""
Unit test suite for FastAPI application skeleton (Task 1.1).
Verifies application factory, OpenAPI specs, docs, health probes, CORS headers, global exception handler, and API v1 routing.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure SQLite in-memory DB for test readiness probe
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import Request
from fastapi.testclient import TestClient
from app.main import app, create_application

client = TestClient(app)


def test_app_factory_creation():
    """1 & 12: Verify create_application factory instantiates a valid FastAPI app."""
    test_app = create_application()
    assert test_app is not None
    assert test_app.title == "AI-Assisted Office Layout Generation Platform API"


def test_health_check_endpoint():
    """2 & 3: Verify GET /healthz returns 200 OK and expected status payload."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "layouts-ai-backend"


def test_readiness_check_endpoint():
    """4: Verify GET /readyz evaluates database connection and returns 200 READY."""
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["database"] == "CONNECTED"


def test_openapi_schema_and_routes():
    """5, 6, 7 & 10: Verify GET /openapi.json returns 200 with healthz and v1 routes."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})

    assert "/healthz" in paths
    assert "/readyz" in paths
    # Verify API v1 routes are mounted
    assert "/api/v1/projects/" in paths or "/api/v1/projects/{project_id}" in paths
    assert "/api/v1/layouts/generate" in paths


def test_swagger_and_redoc_endpoints():
    """8 & 9: Verify GET /docs and GET /redoc return HTTP 200 HTML pages."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger-ui" in docs_resp.text.lower()

    redoc_resp = client.get("/redoc")
    assert redoc_resp.status_code == 200
    assert "redoc" in redoc_resp.text.lower()


def test_cors_middleware_headers():
    """11: Verify CORS middleware adds Access-Control-Allow-Origin for allowed origin."""
    response = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_global_exception_handler():
    """12: Verify global exception handler catches unhandled exceptions and returns HTTP 500."""
    test_app = create_application()

    @test_app.get("/test-error")
    async def trigger_error(request: Request):
        raise ValueError("Simulated unhandled test exception")

    err_client = TestClient(test_app, raise_server_exceptions=False)
    response = err_client.get("/test-error")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal server error occurred."
    assert data["error_type"] == "ValueError"


def test_list_projects_v1_mounted():
    """Verify v1 projects router response."""
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1


def test_generate_layout_v1_mounted():
    """Verify v1 layouts router response."""
    response = client.post("/api/v1/layouts/generate", json={"floor_plan_id": "fp_501"})
    assert response.status_code == 200
    suggestions = response.json()
    assert isinstance(suggestions, list)
    assert len(suggestions) == 2


if __name__ == "__main__":
    test_app_factory_creation()
    test_health_check_endpoint()
    test_readiness_check_endpoint()
    test_openapi_schema_and_routes()
    test_swagger_and_redoc_endpoints()
    test_cors_middleware_headers()
    test_global_exception_handler()
    test_list_projects_v1_mounted()
    test_generate_layout_v1_mounted()
    print("ALL FASTAPI MAIN API TESTS PASSED SUCCESSFULLY!")
