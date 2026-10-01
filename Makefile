.PHONY: help up down test lint migrate

help:
	@echo "AI-Assisted Office Layout Generation Platform"
	@echo "Available commands:"
	@echo "  make up        - Start infrastructure containers (Postgres, Redis)"
	@echo "  make down      - Stop infrastructure containers"
	@echo "  make test      - Run tests across backend, geometry, and frontend"
	@echo "  make lint      - Run linters and code formatting checks"
	@echo "  make migrate   - Run Alembic database migrations"

up:
	docker-compose up -d

down:
	docker-compose down

test:
	pytest geometry/tests backend/tests tests/
	cd frontend && npm test

lint:
	black backend geometry
	flake8 backend geometry
	cd frontend && npm run lint

migrate:
	cd backend && alembic upgrade head
