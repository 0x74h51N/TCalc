.PHONY: dev hooks lint lint-fix typecheck check stubs
.PHONY: py-format py-format-check
.PHONY: native native-configure native-build native-test native-ctest native-clean native-release
.PHONY: py-test py-test-ui py-benchmark

PY := ./.venv/bin/python
PYTEST_ARGS ?= -vv -rA -s

STUBS ?= scripts/stubgen/main.py

stub-gen:
	make -C src/native stub-gen ROOT=$(CURDIR)
	PYTHONPATH=$(CURDIR)/src $(PY) $(STUBS)

dev:
	./scripts/dev

py-lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

py-lint-fix:
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

typecheck:
	$(PY) -m mypy --check-untyped-defs

py-test:
	PYTHONPATH=src $(PY) -m pytest tests/py/unit $(PYTEST_ARGS)
	PYTHONPATH=src $(PY) -m pytest tests/py/ui $(PYTEST_ARGS)
	PYTHONPATH=src $(PY) -m pytest tests/py/e2e $(PYTEST_ARGS)

py-test-ui:
	PYTHONPATH=src $(PY) -m pytest tests/py/ui $(PYTEST_ARGS)

py-benchmark:
	PYTHONPATH=src $(PY) -m pytest tests/benchmark -m benchmark -k "not test_malloc" $(PYTEST_ARGS)

py-mem-profile:
	./scripts/malloc profile

py-mem-flame:
	./scripts/malloc flame

py-mem-tree:
	./scripts/malloc tree

NATIVE_BUILD_TYPE ?= Debug
NATIVE_TEST_ARGS ?= --quiet
STUBS_DIR := stubs

NATIVE_MAKE := $(MAKE) -C src/native \
	ROOT=$(CURDIR) \
	BUILD_TYPE=$(NATIVE_BUILD_TYPE) \
	TEST_ARGS=$(NATIVE_TEST_ARGS)

native: native-build

native-configure:
	$(NATIVE_MAKE) configure

native-build:
	$(NATIVE_MAKE) build
	PYTHONPATH=$(CURDIR)/src $(PY) $(STUBS)

native-test:
	$(NATIVE_MAKE) test

native-ctest:
	$(NATIVE_MAKE) ctest

native-release:
	$(NATIVE_MAKE) release

native-clean:
	$(NATIVE_MAKE) clean

.PHONY: cpp-format cpp-format-check cpp-tidy

cpp-format:
	$(NATIVE_MAKE) cpp-format

cpp-format-check:
	$(NATIVE_MAKE) cpp-format-check

cpp-tidy:
	$(NATIVE_MAKE) cpp-tidy

cpp-tidy-diff:
	$(NATIVE_MAKE) cpp-tidy-diff

hooks:
	$(PY) -m pre_commit install --install-hooks --config .pre-commit.yaml
