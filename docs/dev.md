## Requirements

- Python >= 3.14
- Qt bindings: PySide6
- C++ toolchain
- CMake + Ninja (for native build/test)
- Entr (for dev mode)

### Linux

- g++
- cmake
- ninja
- Boost headers 1.83 or newer (for Multiprecision)
  - Debian/Ubuntu: libboost-dev
  - Fedora: boost-devel
- Python development headers
  - Debian/Ubuntu: python3.14-dev
  - Fedora: python3.14-devel

### macOS

- Xcode Command Line Tools (clang++)
- cmake (Homebrew)
- ninja (Homebrew)
- Boost headers 1.83 or newer (Homebrew)

## Install Deps & Development setup

```bash
make install
```

Dev tooling (`ruff`, `mypy`, `git-cliff`) is installed via the `dev` extra.

The version comes from git tags (setuptools-scm). An editable install shows the version of its last `make install`.

**Build native extension in-place**

```bash
make native-build NATIVE_BUILD_TYPE=Release
```

**Run native tests**

```bash
make native-test
```

**Run app**

```bash
python -m tcalc
```

**Dev mode (auto-restart on changes)**

```bash
make dev
```
