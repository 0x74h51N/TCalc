# CPP Calculator Core

## Requirements

- g++
- Boost headers (for Multiprecision)
  - Debian/Ubuntu: libboost-dev
  - Fedora: boost-devel
- Python development headers
  - Debian/Ubuntu: python3-dev
  - Fedora: python3-devel

## Build

```bash
. venv/bin/activate
python native/setup.py build_ext --inplace
```

This produces `calc_native*.so`
