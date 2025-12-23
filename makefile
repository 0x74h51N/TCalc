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
	rm -f src/calc_native*.so
	cmake -S src/native -B $(NATIVE_BUILD_DIR) -G Ninja \
		-DCMAKE_BUILD_TYPE=$(NATIVE_BUILD_TYPE) \
		-DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
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

.PHONY: cpp-format cpp-format-check cpp-tidy

CPP_FORMAT_FILES := $(shell find src/native -type f \( -name "*.cpp" -o -name "*.hpp" -o -name "*.h" \) -print)
CPP_TIDY_FILES := $(shell find src/native -type f -name "*.cpp" -print)

cpp-format:
	@command -v clang-format >/dev/null || (echo "clang-format not found"; exit 1)
	clang-format -i $(CPP_FORMAT_FILES)

cpp-format-check:
	@command -v clang-format >/dev/null || (echo "clang-format not found"; exit 1)
	@clang-format --dry-run --Werror $(CPP_FORMAT_FILES)

cpp-tidy: native-configure
	@command -v clang-tidy >/dev/null || (echo "clang-tidy not found"; exit 1)
	clang-tidy -quiet -extra-arg=-w -p $(NATIVE_BUILD_DIR) $(CPP_TIDY_FILES)
