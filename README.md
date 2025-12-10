# TCalc

A Python learning project powered by a native C++ calculation core.
The graphical interface is built with PySide6, while all mathematical operations are executed in C++ engine via pybind11 bindings.

Initially focused on basic arithmetic for QT learning, the project is designed to be extended with scientific calculation features in the future.

## Features

- **Expression Parsing**: Infix to RPN conversion using Dijkstra's Shunting Yard Algorithm
- **GUI**: PySide6-based desktop interface
- **Native Core**: C++ calculator engine via pybind11

## Requirements

- Python ≥3.10
- PySide6
- pybind11

## Dev Requirements

- g++
- python3.13-devel
- entr

## Build & Run

Native build:

```bash
python native/setup.py build_ext --inplace
```

Dev mode (auto-restart on changes):

```bash
make dev
```

**Production build:**

Install requirements:

```bash
pip install -e .
```

run:

```bash
python main.py
```

## TODO

- [ ] History panel
- [ ] Keyboard shortcuts
- [ ] Edit menu (undo, redo, cut, copy, paste)
- [ ] Science mode
- [ ] Constant menu
- [ ] Help menu
- [ ] Settings/Config menu

## Credits

The user interface layout and calculator behavior are inspired by KCalc, the KDE Calculator.

## License

MIT
