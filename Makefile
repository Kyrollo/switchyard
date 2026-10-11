# Switchyard Makefile
.PHONY: help install dev test lint clean docker-up docker-down eval docs

help:
	@echo "Available commands:"
	@echo "  install      Install backend and frontend dependencies"
	@echo "  dev          Run both backend and frontend locally in development mode"
	@echo "  test         Run unit, integration, and e2e tests with coverage"
	@echo "  lint         Run ruff, mypy, and no-simulation guards"
	@echo "  docker-up    Start full stack with Docker Compose"
	@echo "  docker-down  Stop Docker Compose stack"
	@echo "  eval         Run evaluation benchmark suite"
	@echo "  docs         Build and serve MkDocs documentation"

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev:
	@echo "Starting development environment..."
	powershell -ExecutionPolicy Bypass -File scripts/dev.ps1

test:
	python scripts/check_no_simulation.py
	cd backend && pytest --cov=src/switchyard --cov-report=term-missing tests/

lint:
	python scripts/check_no_simulation.py
	cd backend && ruff check src/ tests/
	cd backend && mypy src/switchyard
	cd frontend && npm run lint

docker-up:
	docker compose -f deploy/compose.dev.yml up --build

docker-down:
	docker compose -f deploy/compose.dev.yml down

eval:
	python evaluation/harness/runner.py

docs:
	mkdocs serve
