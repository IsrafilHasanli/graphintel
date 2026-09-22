# GraphIntel developer commands.
# On Windows without `make`, run the underlying commands directly.

.PHONY: install data api test lint seed up down fmt

install:
	pip install -e ".[dev,llm]"

# Build the full local demo dataset (download attempt -> synthetic -> processed -> fixtures).
data:
	python scripts/prepare_demo_data.py

validate-data:
	python scripts/validate_demo_data.py

# Run API locally (offline defaults work with SQLite + in-process graph).
api:
	uvicorn app.main:app --reload --app-dir backend --port 8000

# Seed the running API after starting it with `make api` or Docker Compose.
seed: data
	curl -X POST http://localhost:8000/admin/seed

test:
	pytest

lint:
	ruff check backend scripts

fmt:
	ruff check --fix backend scripts

up:
	docker compose up -d --build

down:
	docker compose down
