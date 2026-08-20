# TCalc

A desktop calculator application built around a high-performance native C++ computation core.
The graphical interface is implemented with PySide6; tokenizing, parsing, and evaluating an expression all happen in a dedicated C++ engine exposed to Python via pybind11. An expression crosses into Python only to be displayed.

Originally started as a minimal calculator, TCalc is designed with a modular architecture that supports advanced expression parsing and is intended to evolve toward full scientific and programmable calculation capabilities.

## Features

- **Native C++ core**: tokenize, parse, and evaluate all run in a high-performance C++ engine exposed to Python via pybind11; an expression crosses the boundary once
- **Expression parsing**: infix → RPN (Dijkstra's shunting-yard) over a faithful token model (numbers, ops, parens, LaTeX, calls), all native
- **Structural math rendering**: live LaTeX-style nodes (fractions, powers, parentheses) instead of flat text
- **Collections**: lists `[ … ]` and points `( … )` as first-class values
- **Multi-argument & variadic functions**: one unified call syntax (`mean(2,3,5)`, `gcd(12,8)`, `nCr(5,2)`, `sin(45)`), with arity checks and dataset-folding evaluation
- **Exact arithmetic**: rationals kept exact when possible (decimal ⇄ fraction toggle), with BigReal / complex fallback
- **Scientific functions**: angle-aware trig, logs, combinatorics, number theory, complex-domain rules
- **Iterated operations**: summation (Σ) and product (Π) over a bound variable and range, answered in closed form wherever the body allows it (polynomial, geometric, trigonometric, symbolic constants) instead of looping, with a native brute-force loop as the fallback; the set of recognised bodies keeps growing
- **Composable UI**: dockable panels, custom keypads, keypad presets, readable history (LaTeX → symbols)
- **Well-tested**: native C++ suite + Python unit/e2e coverage with edge cases, plus performance benchmarks

> This project is under heavy development; new features are coming soon. See the detailed [roadmap](./docs/roadmap.md) for more.

## Release Plans

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

### v1 Roadmap

- [ ] Input / Parser / Eval (WiP ~75%)
  - [x] Native pipeline: tokenize → shunting-yard → RPN
  - [x] Collections & function-call (CallToken) evaluation
  - [x] Exact rational arithmetic (decimal ⇄ fraction)
  - [ ] Line-based calc with variables
- [ ] Error handling & messages (WiP ~80%)
- [ ] Calculus
  - [ ] Scientific (WiP ~95%)
    - [x] Scientific function set
    - [ ] Iterated ops (Σ, Π) with closed-form evaluation
  - [ ] Statistic (WiP ~10%)
    - [ ] Statistic operations - normalization/preprocessing, data processing & analysis
    - [ ] Lists & Points - manual or CSV-loaded datasets
- [ ] Menubar (WiP ~40%)
- [ ] History panel (WiP ~75%)
- [ ] Keyboard shortcuts (WiP ~50%)
- [ ] GUI / UX / Accessibility (WiP ~50%)
  - [x] Dock layout w/ custom pads
  - [ ] Math nodes w/ LaTeX rendering (WiP ~70%)
- [ ] Packaging
- [ ] Tests (WiP ~75%)

### v2 Roadmap

- [ ] Science mode improvements
  - [ ] Numeric calculus: derivative, definite integral, limit
  - [ ] Vector & matrix operations (dot, cross, length, det, inv)
- [ ] Programmer mode
  - [ ] Binary/hex/oct/dec input, bitwise operations, width handling
- [ ] Graphic mode
  - [ ] Function plotting, zoom/pan, discontinuity handling
- [ ] Localization

See the detailed [roadmap](./docs/roadmap.md)

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
