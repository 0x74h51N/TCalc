# TCalc

A Python learning project powered by a native C++ calculation core.
The graphical interface is built with PySide6, while all mathematical operations are executed in C++ engine via pybind11 bindings.

Initially focused on basic arithmetic for QT learning, the project is designed to be extended with scientific calculation features in the future.

## Features

- **Expression Parsing**: Infix to RPN conversion using Dijkstra's Shunting Yard Algorithm
- **GUI**: PySide6-based desktop interface
- **Native Core**: C++ calculator engine via pybind11

## Requirements

- Python >= 3.10
- PySide6
- pybind11

## Development Requirements

### Cross-platform (required)
- Python >= 3.10
- pip
- setuptools
- wheel

### Windows (native build)
- Microsoft Visual C++ Build Tools (MSVC)
  - Install "Desktop development with C++"

### Linux (native build)
- g++
- Python development headers  
  - Debian/Ubuntu: `python3-dev`
  - Fedora: `python3-devel`

### Optional (Linux dev tooling)
- entr (for auto-reload dev mode)

## Installation

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e .
```

**Native Extension Build**

Build the C++ extension in-place:

```bash
python native/setup.py build_ext --inplace
```
run:

```bash
python main.py
```

Dev mode (auto-restart on changes):

```bash
make dev
```


## v1 Plan

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

### v1 Roadmap
- [ ] History panel
  - [x] Add history panel with open/close shortcut
  - [ ] Make max history item count configurable in general settings
  - [ ] Allow disabling history persistence (local storage) via settings
- [ ] Keyboard shortcuts in app level w/button animate
- [x] Edit menu (undo, redo, cut, copy, paste)
- [ ] Science mode
  - [ ] MS, MC, MR, M+
  - [x] Trigonometry operations
  - [x] deg, rad, grad
  - [ ] Logarithm, exponent, factorial, reciprocal, modulo
  - [ ] Shift-modified operations (Γ, intDiv, inverse trigonometry, binomial coefficients etc.)
  - [ ] (Maybe) derivative, integral, and limit
  - [ ] (Maybe²) vector operations: length, dot, cross
  - [ ] (Maybe³) matrix operations: multiplication, inverse, determinant
- [ ] Statistic mode
  - [ ] Data store and statistic operations: mean, standart deviation, median etc.
- [ ] Constant menu
- [ ] Help menu
  - [ ] Find Action
  - [ ] About etc.
- [ ] Settings/Config menu
  - [ ] Programable constant buttons
  - [ ] Configure TCalc
    - [ ] General conf
    - [ ] Fonts
    - [ ] Themes
    - [ ] Constants
  - [ ] Configure keyboard shortcuts
- [ ] Improve styles and layout design

### v1 Releases
- Windows
- Linux
- macOS

## Credits

The user interface layout and calculator behavior are inspired by KCalc, the KDE Calculator.

## License

MIT
