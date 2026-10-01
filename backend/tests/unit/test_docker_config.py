"""
Unit test verifying Docker infrastructure and GitHub Actions CI workflow (Task 1.5).
Inspects Dockerfile, docker-compose.yml, and .github/workflows/ci.yml configuration integrity.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


def test_docker_compose_file_structure():
    docker_compose_path = ROOT_DIR / "docker-compose.yml"
    assert docker_compose_path.exists(), "docker-compose.yml file is missing!"

    content = docker_compose_path.read_text(encoding="utf-8")
    assert "postgis/postgis:16-3.4" in content, "PostgreSQL+PostGIS container missing in docker-compose.yml"
    assert "redis:7-alpine" in content, "Redis container missing in docker-compose.yml"
    assert "minio/minio" in content, "MinIO container missing in docker-compose.yml"
    assert "backend_api" in content, "Backend API service missing in docker-compose.yml"


def test_backend_dockerfile_structure():
    dockerfile_path = ROOT_DIR / "backend" / "Dockerfile"
    assert dockerfile_path.exists(), "backend/Dockerfile file is missing!"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "python:3.11-slim" in content, "Python 3.11 base image missing in Dockerfile"
    assert "EXPOSE 8000" in content, "Expose 8000 port declaration missing in Dockerfile"


def test_github_actions_ci_structure():
    ci_path = ROOT_DIR / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists(), ".github/workflows/ci.yml file is missing!"

    content = ci_path.read_text(encoding="utf-8")
    assert "actions/checkout" in content, "Checkout step missing in CI workflow"
    assert "test_domain_schemas.py" in content, "Test step missing in CI workflow"


if __name__ == "__main__":
    test_docker_compose_file_structure()
    test_backend_dockerfile_structure()
    test_github_actions_ci_structure()
    print("ALL DOCKER & CI/CD INFRASTRUCTURE TESTS PASSED SUCCESSFULLY!")
