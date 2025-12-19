.PHONY: configure build test ctest clean release

ROOT ?= ../..
BUILD_DIR ?= $(ROOT)/build/native
BUILD_TYPE ?= Debug
PYTHON ?= $(ROOT)/venv/bin/python
TEST_ARGS ?= --quiet

configure:
	cmake -S . -B $(BUILD_DIR) -G Ninja \
		-DCMAKE_BUILD_TYPE=$(BUILD_TYPE) \
		-DPython3_EXECUTABLE="$(PYTHON)"

build: configure
	cmake --build $(BUILD_DIR) -j

test: build
	$(BUILD_DIR)/native_tests $(TEST_ARGS)

ctest: build
	ctest --test-dir $(BUILD_DIR) --output-on-failure

release:
	$(MAKE) test BUILD_TYPE=Release

clean:
	rm -rf $(BUILD_DIR)

