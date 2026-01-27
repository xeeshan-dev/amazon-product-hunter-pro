# Makefile for Amazon Hunter Pro

.PHONY: help install dev test lint format clean docker-build docker-up docker-down logs

help:
	@echo "Amazon Hunter Pro - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install dependencies"
	@echo "  make dev           Run development server"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker images"
	@echo "  make docker-up     Start all services"
	@echo "  make docker-down   Stop all services"
	@echo "  make logs          View logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove cache and temp files"

install:
	pip install -r requirements.txt
	pip install -r web_app/backend/requirements.txt
	pip install pytest pytest-cov pytest-asyncio httpx flake8 black isort

dev:
	uvicorn web_app.backend.main_v2:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov --cov-report=html --cov-report=term

lint:
	flake8 src/ web_app/backend/ --max-line-length=120 --exclude=__pycache__
	black --check src/ web_app/backend/
	isort --check-only src/ web_app/backend/

format:
	black src/ web_app/backend/
	isort src/ web_app/backend/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Health: http://localhost:8000/health"

docker-down:
	docker-compose down

docker-restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-celery:
	docker-compose logs -f celery_worker

shell:
	docker-compose exec api /bin/bash

db-migrate:
	docker-compose exec api alembic upgrade head

db-rollback:
	docker-compose exec api alembic downgrade -1

redis-cli:
	docker-compose exec redis redis-cli

psql:
	docker-compose exec postgres psql -U amazon_hunter -d amazon_hunter
