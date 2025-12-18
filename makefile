.PHONY: dev hooks lint lint-fix typecheck check

PY := ./venv/bin/python

dev: hooks
	./scripts/dev

lint:
	$(PY) -m ruff check src
	$(PY) -m ruff format --check src

lint-fix:
	$(PY) -m ruff check --fix src
	$(PY) -m ruff format src

typecheck:
	$(PY) -m mypy

check: lint typecheck
