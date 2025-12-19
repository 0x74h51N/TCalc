cmake_minimum_required(VERSION 3.20)

project(tcalc_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

# Prefer the pybind11 that is installed into the active Python environment (venv).
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
  OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE
  RESULT_VARIABLE PYBIND11_CMAKE_DIR_RESULT
)
if(PYBIND11_CMAKE_DIR_RESULT EQUAL 0 AND EXISTS "${PYBIND11_CMAKE_DIR}")
  list(PREPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
endif()

find_package(pybind11 CONFIG REQUIRED)

add_library(calc_core STATIC
  lib/arithmetic.cpp
  lib/transcendental.cpp
  lib/trig.cpp
  lib/combinatorics.cpp
)
target_include_directories(calc_core PUBLIC
  "${CMAKE_CURRENT_LIST_DIR}/lib/pub"
  "${CMAKE_CURRENT_LIST_DIR}/lib"
)

add_executable(native_tests
  tests/main.cpp
  tests/unit/test_arithmetic.cpp
  tests/unit/test_transcendental.cpp
  tests/unit/test_trig.cpp
  tests/unit/test_combinatorics.cpp
  tests/smoke/smoke_stress.cpp
)
target_include_directories(native_tests PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}/tests"
  "${CMAKE_CURRENT_LIST_DIR}/lib/pub"
  "${CMAKE_CURRENT_LIST_DIR}/lib"
)
target_link_libraries(native_tests PRIVATE calc_core)

enable_testing()
add_test(NAME native_tests_quiet COMMAND native_tests --quiet)

pybind11_add_module(calc_native
  python/module.cpp
  python/bindings/bind_bigreal.cpp
  python/bindings/bind_angle_unit.cpp
  python/bindings/bind_calculator.cpp
)
target_include_directories(calc_native PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}/python/include"
  "${CMAKE_CURRENT_LIST_DIR}/lib/pub"
  "${CMAKE_CURRENT_LIST_DIR}/lib"
)
target_link_libraries(calc_native PRIVATE calc_core)


set_target_properties(calc_native PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/.."
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/.."
  PREFIX ""
)

