.PHONY: help setup lint test format typecheck run run-dev backend frontend clean

help:
	@echo "Croc-Bot Trading System - Available Commands"
	@echo "============================================="
	@echo "  setup       - Install dependencies (run scripts/setup.sh or scripts/setup.ps1)"
	@echo "  lint        - Run ruff linter on backend"
	@echo "  format      - Format code with ruff"
	@echo "  typecheck   - Run mypy type checker"
	@echo "  test        - Run pytest tests"
	@echo "  run         - Run backend in production mode"
	@echo "  run-dev     - Run backend in development mode (with reload)"
	@echo "  backend     - Alias for run-dev"
	@echo "  frontend    - Run frontend development server"
	@echo "  clean       - Remove temporary files and caches"

setup:
	@echo "Run the appropriate setup script:"
	@echo "  Windows: powershell -ExecutionPolicy Bypass -File scripts\\setup.ps1"
	@echo "  Linux/Mac: bash scripts/setup.sh"

lint:
	@echo "Running ruff linter..."
	ruff check backend/crippel --fix

format:
	@echo "Formatting code with ruff..."
	ruff format backend/crippel

typecheck:
	@echo "Running mypy type checker..."
	cd backend && mypy crippel --strict

test:
	@echo "Running pytest..."
	cd backend && pytest -v --cov=crippel --cov-report=term-missing

run:
	@echo "Starting backend (production mode)..."
	cd backend && uvicorn crippel.app:app --host 0.0.0.0 --port 8000

run-dev:
	@echo "Starting backend (development mode with reload)..."
	cd backend && uvicorn crippel.app:app --reload --host 0.0.0.0 --port 8000

backend: run-dev

frontend:
	@echo "Starting frontend development server..."
	cd frontend && npm run dev

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"
