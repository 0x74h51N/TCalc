.PHONY: dev hooks lint lint-fix typecheck check stubs
.PHONY: py-format py-format-check
.PHONY: native native-configure native-build native-test native-ctest native-clean native-release
.PHONY: py-test

PY := ./venv/bin/python
PYTEST_ARGS ?= -vv -rA

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

py-format:
	$(PY) -m ruff format src

py-format-check:
	$(PY) -m ruff format --check src

py-test:
	PYTHONPATH=src $(PY) -m pytest $(PYTEST_ARGS)


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
