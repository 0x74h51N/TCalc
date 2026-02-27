# TCalc

A desktop calculator application built around a high-performance native C++ computation core.
The graphical interface is implemented with PySide6, while all mathematical operations are executed in a dedicated C++ engine exposed to Python via pybind11.

Originally started as a minimal calculator, TCalc is designed with a modular architecture that supports advanced expression parsing and is intended to evolve toward full scientific and programmable calculation capabilities.

## Features

- **Expression Parsing**: Infix to RPN conversion using Dijkstra's Shunting Yard Algorithm
- **GUI**: PySide6-based desktop interface
- **Native Core**: C++ calculator engine via pybind11

## Release Plans

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

### v1 Roadmap

- [ ] History panel
- [ ] Keyboard shortcuts (custom editable)
- [ ] Calculator Modes
  - [x] Simple mode
  - [x] Science mode (trig, log, pow, complex)
  - [ ] Statistic mode (dataset, summary)
- [ ] GUI / UX / Accessibility
  - [ ] Expression GUI nodes (fractions, pow, root, log)
  - [ ] Toggleable LaTeX rendering (raw string <-> rendered)
  - [ ] Layout, tab order, high-DPI support, tooltips
- [ ] Menubar / Settings
  - [ ] File, Edit, Constant, Help, Settings menus
  - [ ] Configurable constants, keyboard shortcuts, themes, precision
- [ ] Dev / Packaging / Tests

### v2 Roadmap

- [ ] Science mode improvements
  - [ ] Variable-based expressions and function input
  - [ ] Numeric calculus: derivative, definite integral, limit
  - [ ] Vector operations (dot, cross, length)
- [ ] Programmer mode
  - [ ] Binary/hex/oct/dec input, bitwise operations, width handling
- [ ] Graphic mode
  - [ ] Function plotting, zoom/pan, discontinuity handling
- [ ] Localization

## Contributing & Feedback

Bug reports, feature requests, and general feedback are welcome.
If you encounter an issue or have an improvement suggestion, feel free to open an issue.

Contributions are also welcome via pull requests.

[Dev doc](docs/dev.md)

## Credits

- The user interface layout and calculator behavior are inspired by KCalc, the KDE Calculator.
- The mathematical GUI renderings via LaTeX, is inspired by Desmos Scientific Calculator.

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

For more details, see the [LICENSE](LICENSE) file in the root directory.

---
Copyright (C) 2025 Tahsin Önemli
