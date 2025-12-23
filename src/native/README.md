# CPP Calculator Core

## Requirements

- g++
- cmake
- ninja
- Boost headers (for Multiprecision)
  - Debian/Ubuntu: libboost-dev
  - Fedora: boost-devel
- Python development headers
  - Debian/Ubuntu: python3-dev
  - Fedora: python3-devel
    macOS:
- Xcode Command Line Tools (clang++)
- Boost headers (Homebrew)

## Dev tools

Liny & Formatter:

- `clang-format`
- `clang-tidy`y

- Debian/Ubuntu: `sudo apt-get install clang-format clang-tidy`
- Fedora: `sudo dnf install clang-tools-extra`
- macOS (Homebrew): `brew install clang-format llvm`

## Build

```bash
. venv/bin/activate
make -C src/native build BUILD_TYPE=Release
```

This produces `src/calc_native*.so`

## Tests (no Python)

Linux/macOS:

```bash
make -C src/native test
```

## Formatting / Lint

From repo root:

- Format: `make cpp-format`
- Check formatting: `make cpp-format-check`
- Lint: `make cpp-tidy` (runs `native-configure` to generate `build/native/compile_commands.json`)
