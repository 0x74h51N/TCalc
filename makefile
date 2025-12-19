.PHONY: dev hooks lint lint-fix typecheck check
.PHONY: native native-configure native-build native-test native-ctest native-clean native-release

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

NATIVE_BUILD_DIR := build/native
NATIVE_BUILD_TYPE ?= Debug
NATIVE_TEST_ARGS ?= --quiet

native-configure:
	cmake -S src/native -B $(NATIVE_BUILD_DIR) -G Ninja \
		-DCMAKE_BUILD_TYPE=$(NATIVE_BUILD_TYPE) \
		-DPython3_EXECUTABLE="$(PY)"

native-build: native-configure
	cmake --build $(NATIVE_BUILD_DIR) -j

native-test: native-build
	$(NATIVE_BUILD_DIR)/native_tests $(NATIVE_TEST_ARGS)

native-ctest: native-build
	ctest --test-dir $(NATIVE_BUILD_DIR) --output-on-failure

native: native-test

native-release:
	$(MAKE) native NATIVE_BUILD_TYPE=Release

native-clean:
	rm -rf $(NATIVE_BUILD_DIR)
