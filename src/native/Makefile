.PHONY: configure build test ctest clean release
.PHONY: cpp-format cpp-format-check cpp-tidy

ROOT := ../..
BUILD_DIR := $(ROOT)/build/native
BUILD_TYPE ?= Debug
PYTHON := $(ROOT)/venv/bin/python
TEST_ARGS ?= --quiet
STUBS_DIR := $(ROOT)/stubs

CPP_FORMAT_FILES := $(shell find $(ROOT)/src/native -type f \( -name "*.cpp" -o -name "*.hpp" -o -name "*.h" \) -print)
CPP_TIDY_FILES := $(shell find $(ROOT)/src/native -type f -name "*.cpp" -print)

configure:
	rm -f $(ROOT)/src/calc_native*.so
	cmake -S . -B $(BUILD_DIR) -G Ninja \
		-DCMAKE_BUILD_TYPE=$(BUILD_TYPE) \
		-DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
		-DPython3_EXECUTABLE="$(PYTHON)"

build: configure
	cmake --build $(BUILD_DIR) -j
	PYTHONPATH=$(ROOT)/src $(PYTHON) -m pybind11_stubgen calc_native -o $(STUBS_DIR)
	PYTHONPATH=$(ROOT)/src $(ROOT)/venv/bin/stubgen --verbose --inspect-mode -m tcalc.core.ops -o $(STUBS_DIR)

test: build
	$(BUILD_DIR)/native_tests $(TEST_ARGS)

ctest: build
	ctest --test-dir $(BUILD_DIR) --output-on-failure

release:
	$(MAKE) test BUILD_TYPE=Release

clean:
	rm -rf $(BUILD_DIR)

cpp-format:
	@command -v clang-format >/dev/null || (echo "clang-format not found"; exit 1)
	clang-format -i $(CPP_FORMAT_FILES)

cpp-format-check:
	@command -v clang-format >/dev/null || (echo "clang-format not found"; exit 1)
	@clang-format --dry-run --Werror $(CPP_FORMAT_FILES)

cpp-tidy: configure
	@command -v clang-tidy >/dev/null || (echo "clang-tidy not found"; exit 1)
	clang-tidy -quiet -extra-arg=-w -p $(BUILD_DIR) $(CPP_TIDY_FILES)

stub-gen: $(SO_FILE)
	PYTHONPATH=$(ROOT)/src $(PYTHON) -m pybind11_stubgen calc_native -o $(ROOT)/stubs
