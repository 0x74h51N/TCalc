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
- Boost headers (for Multiprecision)
  - Debian/Ubuntu: libboost-dev
  - Fedora: boost-devel
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
python -m pip install -e ".[dev]"
```

Dev tooling (`ruff`, `mypy`) is installed via the `dev` extra.

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

Dev tools - lint/type-check

```bash
make lint       # find issues
make lint-fix   # auto-fix what ruff can
make typecheck  # mypy
make check      # lint + typecheck
```

## Release Plans

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

### v1 Roadmap

- [ ] History panel
  - [x] Add history panel with open/close shortcut
  - [x] Make separate history for calc modes
  - [ ] Make max history item count configurable in general settings
  - [ ] Allow disabling history persistence (local storage) via settings
  - [ ] Export as text file
- [ ] Keyboard shortcuts

  - [x] Basic shortcuts and handlers (cut, copy, undo, redo, quit etc.)
  - [ ] Configurable shortcuts, bind/apply via a configuration window

- [x] Memory for all modes MS, MC, MR, M+ Buttons

- [ ] Input / Parser / Eval

  - [x] Expression pipeline: tokenize -> normalize -> shunting-yard -> RPN eval
  - [x] Unary/prefix/postfix handling + mode-based domain behavior (sqrt(-4): real MathError, complex 2i)
  - [x] Undo/redo integrates with history navigation (rebuild expression from previous calc and auto-eval)
  - [x] Error mapping spec (engine -> UI)
  - [ ] Test edge cases

- [ ] Calc Modes

  - [x] Mode state, layout update, binding and side effects
  - [x] Simple Mode

  - [ ] Science mode

    - [x] UI / Controls
      - [x] Science keypad panel
      - [x] Angle unit radios (Deg/Rad/Grad) - state/binding
      - [x] Shift toggles and shift keys
    - [x] Trigonometry
      - [x] sin/cos/tan (angle-aware)
      - [x] Hyp toggle and hyperbolic keys (sinh/cosh/tanh)
      - [x] inverse trig via Shift (asin/acos/atan or asinh/acosh/atanh)
    - [x] Functions - log10/ln, 1/x, x!, mod, permutation/choose
    - [x] Power / Complex - sqrt, x², xʸ, exp10, i, complex domain rules
    - [x] Parser parity - Implement ops in native + pybind
    - [ ] Edge cases + error messages

  - [ ] Statistic mode
    - [ ] Data store
      - [ ] Add/remove/clear data points
      - [ ] Optional dataset persistence toggle (def false)
    - [ ] Data panel UI
      - [ ] Place to the right of History with a vertical separator (History panel expands)
      - [ ] Show dataset list + summary (n, Σx, Σx²)
      - [ ] Show dataset change log (added/removed/cleared)
    - [ ] Keypad integration (left panel)
      - [ ] Statistic operations as buttons (mean, median, min, max)
      - [ ] variance + standard deviation (sample vs population)
      - [ ] Shift toggles secondary operations (Σx, Σx², etc.)
    - [ ] Native + parser parity
      - [ ] Implement ops in native + pybind
      - [ ] Ensure parser maps symbols/aliases correctly
    - [ ] Edge cases + error messages

- [ ] Menubar

  - [x] File menu
  - [x] Edit menu (undo, redo, cut, copy, paste), binding/apply
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
