.PHONY: setup lint type test gate up down

PYTHON := uv run
COMPOSE := docker compose -f infra/docker-compose.yml

setup:
	$(PYTHON) sync --all-packages
	pnpm install

lint:
	$(PYTHON) ruff check .
	$(PYTHON) ruff format --check .
	pnpm --dir apps/web lint

type:
	$(PYTHON) mypy
	pnpm --dir apps/web typecheck

test:
	$(PYTHON) pytest
	pnpm --dir apps/web test

gate:
	$(PYTHON) lint-imports
	$(PYTHON) pytest tests/contracts
	$(PYTHON) pytest -m gate packages/eval/tests
	$(PYTHON) pytest --cov=uni_rag_core --cov-report=term-missing --cov-fail-under=80

up:
	$(COMPOSE) up -d --wait

down:
	$(COMPOSE) down -v
