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
