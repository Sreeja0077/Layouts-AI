"""
Unit test for FastAPI application routes (Task 1.1).
Tests /healthz, /readyz, and API v1 endpoints using TestClient.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "layouts-ai-backend"


def test_readiness_check():
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "READY"


def test_list_projects_endpoint():
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert len(projects) > 0
    assert projects[0]["id"] == "proj_101"


def test_generate_layout_endpoint():
    response = client.post("/api/v1/layouts/generate", json={"floor_plan_id": "fp_501"})
    assert response.status_code == 200
    suggestions = response.json()
    assert isinstance(suggestions, list)
    assert len(suggestions) == 2
    assert suggestions[0]["strategy_name"] == "Perimeter High-Density Strategy"


if __name__ == "__main__":
    test_health_check()
    test_readiness_check()
    test_list_projects_endpoint()
    test_generate_layout_endpoint()
    print("ALL FASTAPI MAIN API TESTS PASSED SUCCESSFULLY!")
