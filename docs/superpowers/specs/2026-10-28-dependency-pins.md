# Dependency pins

What was pinned on 2026-10-28 (PR #93, `chore/pin-deps`) and why, and what is left to do with the pins.

## Why

Nothing was pinned, so every fresh install took the newest versions and environments drifted:

- PySide6 6.10.2 invalidated the Python wrapper that `QAction.menu()` returns once the action's wrapper was collected (5 theme tests failed), and docks could not be dragged. Both are fine on 6.12.
- pytest 9.2.0 (released 2026-10-27) removed `Node._nodeid`, which pytest-benchmark 5.3.0, the latest, still reads, so every benchmark errored at setup.
- Local clang-format and clang-tidy were 21 while CI used 20 (format) and 18 (tidy).

## What is pinned

Every dependency is pinned to its minor version; only patch releases come in.

- Build: setuptools 84.2.x, wheel 0.48.x, pybind11 3.1.x
- Runtime: PySide6 6.12.x, pybind11 3.1.x
- Dev: pytest 9.1.x, pytest-benchmark 5.3.x, pytest-qt 4.5.x, pytest-memray 1.11.x, mypy 2.4.x, pre-commit 4.7.x, pybind11-stubgen 3.0.x, pyinstrument 5.1.x, ruff 0.15.0, clang-format 21.1.x, clang-tidy 21.1.x
- Python 3.14.x (`requires-python`, ruff and pyright target 3.14, CI runs 3.14.5 only)
- CI: pip 26.2.x
- Boost: 1.83 or 1.84, checked by CMake at configure time

clang-format and clang-tidy come from the venv, the same versions locally and in CI. `run-clang-tidy` stays the system driver script (Fedora `clang-tools-extra`, Ubuntu `clang-tidy`, macOS `llvm`).

## install-deps

- The venv runs on `python3.14`. A system python that is already 3.14 is used; otherwise 3.14 is installed next to it (Fedora `python3.14`, Ubuntu deadsnakes PPA, macOS `python@3.14`). The system's default python is never changed. A venv made by another version is made again.
- Checked cases: Fedora 43 with system 3.14 (nothing installed), Ubuntu 24.04 with system 3.12 in a container (3.14 installed next to it, `python3` stays 3.12). macOS is not checked.
- The OS block sets `PKG_CHECK` and `PKG_INSTALL` once; Ubuntu runs `apt-get update` once.
- Other systems (Arch and the rest) get no package installs, only a list of what to install. The venv, pip and hooks steps still run if `python3.14` is there.
- Git hooks are installed again; splitting the dev and install-deps scripts had dropped `make hooks`.

## Left

1. Boost: when a Boost release with the `fmod` fix is out, raise the CMake upper bound (`src/native/CMakeLists.txt`) and the Boost line in `docs/dev.md`. TCalc's own results do not depend on it (`mod` and `intdiv` use `calc_detail::trunc_div`), so this only widens what installs.
2. pytest: move past 9.1.x together with pytest-benchmark once a pytest-benchmark release works with pytest 9.2 (it reads `Node._nodeid`).
3. GitHub Actions: `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4` and `download-artifact@v4` target Node.js 20, which GitHub deprecates (each run warns). Move them to the majors that run on Node.js 24.
4. macOS: `install-deps` is not tried there. Homebrew ships the newest Boost, which the configure check refuses, so a macOS setup needs Boost 1.83 or 1.84 from somewhere else.
5. Upgrading any pin: bump it on its own branch, run the whole suite (benchmarks included, `make py-benchmark` and `make py-mem-profile`) before merging.
