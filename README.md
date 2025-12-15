# TCalc

A desktop calculator application built around a high-performance native C++ computation core.
The graphical interface is implemented with PySide6, while all mathematical operations are executed in a dedicated C++ engine exposed to Python via pybind11.

Originally started as a minimal calculator, TCalc is designed with a modular architecture that supports advanced expression parsing and is intended to evolve toward full scientific and programmable calculation capabilities.

## Features

- **Expression Parsing**: Infix to RPN conversion using Dijkstra's Shunting Yard Algorithm
- **GUI**: PySide6-based desktop interface
- **Native Core**: C++ calculator engine via pybind11

## Requirements

- Python >= 3.10
- Qt bindings: PySide6
- C++ toolchain (only if you build the native extension)

## Native build prerequisites (if needed)

### Windows

- MSVC Build Tools (Desktop development with C++)

### Linux

- g++
- Python development headers
  - Debian/Ubuntu: python3-dev
  - Fedora: python3-devel

### Optional (Linux dev tooling)

- entr (auto-restart dev mode)

## Development setup (recommended)

Create and use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

**Build native extension in-place**

```bash
python src/native/setup.py build_ext --inplace
```

**Run app**

```bash
python -m tcalc
```

Dev mode (auto-restart on changes):

```bash
make dev
```

## Release Plans

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

### v1 Roadmap

- [ ] History panel
  - [x] Add history panel with open/close shortcut
  - [ ] Make seperate history for calc modes
  - [ ] Make max history item count configurable in general settings
  - [ ] Allow disabling history persistence (local storage) via settings
  - [ ] Export as text
- [ ] Keyboard shortcuts in app level w/button animate
- [x] Edit menu (undo, redo, cut, copy, paste)
- [ ] Memory for all modes MS, MC, MR, M+ Buttons

- [ ] Input / Parser / Eval

  - [x] Expression pipeline: tokenize -> normalize -> shunting-yard -> RPN eval
  - [x] Unary/prefix/postfix handling + mode-based domain behavior (sqrt(-4): real MathError, complex 2i)
  - [x] Undo/redo integrates with history navigation (rebuild expression from previous calc and auto-eval)
  - [x] Error mapping spec (engine -> UI)
  - [ ] Test edge cases

- [ ] Science mode
  - [x] Trigonometry operations
  - [x] deg, rad, grad
  - [ ] Logarithm, exponent, factorial, reciprocal, modulo
  - [ ] Shift-modified operations (Gamma, intDiv, inverse trigonometry, binomial coefficients etc.)
- [ ] Statistic mode
  - [ ] Data store and statistic operations: mean, standart deviation, median etc.
- [ ] Constant menu
  - [ ] All math or physic constants on menu
  - [ ] All constants side panel window
- [ ] Help menu
  - [ ] Find Action
  - [ ] User manual
  - [ ] About, vers, licance etc.
- [ ] Settings/Config menu
  - [ ] Programable constant buttons
  - [ ] Configure TCalc
    - [ ] General conf
      - [ ] Max number of digits, precision
    - [ ] Fonts
    - [ ] Themes
    - [ ] Constants
  - [ ] Configure keyboard shortcuts
- [ ] Improve styles and layout design

- [ ] UX / Accessibility

  - [ ] Tab order + focus behavior
  - [ ] High-DPI/font scaling sanity pass
  - [ ] Basic tooltips for all keys

- [ ] Packaging

  - [ ] Versioning + build metadata
    - [ ] App version (SemVer) + build number
    - [ ] About: version, platform, Qt/PySide version, commit hash
  - [ ] Runtime paths
    - [ ] Use QStandardPaths for config/data/logs paths
    - [x] Document where history/settings are stored (QSettings)
  - [ ] Crash log (minimum)
    - [ ] Unhandled exception hook -> log file
    - [ ] Help/About: "Open logs folder" or "Copy debug info"
  - [ ] Windows packaging
    - [ ] Build artifact (PyInstaller or Nuitka)
    - [ ] installer .exe
  - [ ] Linux packaging
    - [ ] AppImage
  - [ ] macOS packaging
    - [ ] .app bundle + dmg/zip distribution

- [ ] Tests (native core + pipeline)
  - [ ] Core unit tests (engine)
  - [ ] Parser pipeline tests (tokenize -> normalize -> shunting-yard -> RPN eval)
  - [ ] Edge cases / regression tests (add to golden list)
  - [ ] UI smoke tests

### v2 Roadmap

- [ ] Science mode improvements
  - [ ] Variable-based expression support (function input)
    - [ ] Support identifiers (start with `x`) in tokenizer/parser
    - [ ] Evaluation context: evaluate expressions with `x = value`
    - [ ] Function-style input (optional): `f(x) = <expr>` / reuse `<expr>` directly
  - [ ] Calculus (numeric)
    - [ ] Derivative (numeric)
      - [ ] `d/dx` at a point: `f'(a)` (auto step size)
    - [ ] Definite integral (numeric)
      - [ ] `int_a^b f(x) dx` (choose method: Simpson / adaptive Simpson)
      - [ ] Handle invalid ranges / discontinuities with clear errors
    - [ ] Limit (numeric)
      - [ ] `lim x->a f(x)` with side options: both / left / right
      - [ ] Detect non-convergence / undefined cases and show proper error
  - [ ] Vector and operations: length, dot, cross
    - [ ] Vector Mode: add `vec(a,b,...)` input and typed eval (Scalar or Vector)
    - [ ] Rules: `s*v` / `v*s` scales, `v+v` / `v-v` only if same dimension, `v/s` ok, `v+s` and `v*v` invalid (use `dot(v,w)`, `cross(v,w)`), `length(v)` -> scalar
- [ ] Programmer Mode (Numeral system)
  - [ ] Binary input and output
  - [ ] Hex, dec, oct, bin modes
  - [ ] Logical and bit operations
  - [ ] Bit width + signed/unsigned (8/16/32/64) and overflow behavior
  - [ ] Bitwise shifts, rotate
  - [ ] Two's complement display for negatives (define the rule)
- [ ] Graphic Mode
  - [ ] Graphic drawing to equations or calculations
  - [ ] Graph screen and axes with inf length
  - [ ] Function input + domain/range + sampling step (perf/quality knob)
  - [ ] Zoom/pan + reset view
  - [ ] Discontinuity handling (break lines at asymptotes)
- [ ] Localization
  - [ ] Locale-aware decimal separator + formatting & input (comma/dot)
  - [ ] Thousands separator formatting (space/comma/dot) and copy behavior

## Contributing & Feedback

Bug reports, feature requests, and general feedback are welcome.
If you encounter an issue or have an improvement suggestion, feel free to open an issue.

Contributions are also welcome via pull requests.

## Credits

The user interface layout and calculator behavior are inspired by KCalc, the KDE Calculator.

## License

MIT
