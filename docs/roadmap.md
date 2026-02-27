
## Release Plans

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

### v1 Roadmap

- [ ] History panel
  - [x] Add history panel with open/close shortcut
  - [x] Make separate history for calc modes
  - [ ] Make history items design more pleasant and add copy icon (auto copy -> copy icon)
  - [ ] Make max history item count configurable in general settings
  - [ ] Make human readable history items formatter (LaTeX -> math symbols)
  - [ ] Allow disabling history persistence (local storage) via settings
  - [ ] Export as text file

- [ ] Keyboard shortcuts
  - [x] Basic shortcuts and handlers (cut, copy, undo, redo, quit etc.)
  - [ ] Configurable shortcuts, bind/apply via a configuration window

- [x] Memory for all modes MS, MC, MR, M+ Buttons

- [x] Input / Parser / Eval

  - [x] Expression pipeline: tokenize -> shunting-yard -> RPN Evaluation
    - [x] Tokenize Parser
      - [x] Add native tokenize and shunting-yard functions
      - [x] Add distinct token kinds (number, op, paren, expr)
      - [x] Add LaTeX expression parser on Native
        - [x] Add ExprToken w/left/right sub tokens (AST-like)
        - [x] Parse LaTeX expressions into token nodes
      - [x] Add parentheses parser on native
        - [x] Add paren kinds and open/close types
        - [x] Add open and close indices with paren kinds (to split and convert ParenNode in GUI)
      - [x] Add source range tracking (start_pos, end_pos) to tokens
      - [x] Add structural indices for LaTeX expressions and parentheses
      - [x] Add normalize function for implicit multiplications or plus to minus
    - [x] Add Shunting-yard
    - [x] Add RPN evaluation in Python (for minimal boilerplate)  
    - [x] Unary/prefix/postfix handling + mode-based domain behavior (sqrt(-4): real MathError, complex 2i)
  - [x] Undo/redo integrates with history navigation (rebuild expression from previous calc and auto-eval)
  - [x] Error mapping spec (engine -> UI)
  - [x] Test edge cases

- [ ] Calc Modes

  - [x] Mode state, layout update, binding and side effects
  - [x] Simple Mode

  - [x] Science mode

    - [x] UI / Controls
      - [x] Science keypad panel
      - [x] Angle unit radios (Deg/Rad/Grad) - state/binding
      - [x] Shift toggles and shift keys
    - [x] Trigonometry
      - [x] sin/cos/tan (angle-aware)
      - [x] Hyp toggle and hyperbolic keys (sinh/cosh/tanh)
      - [x] inverse trig via Shift (asin/acos/atan or asinh/acosh/atanh)
    - [x] Functions - log10/ln, 1/x, x!, mod, permutation/choose
    - [x] Power / Complex - sqrt, x², xʸ, i, complex domain rules
    - [x] Parser parity - Implement ops in native + pybind
    - [x] Edge cases + error messages

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

- [ ] GUI / UX / Accessibility
  - [ ] Improve styles and layout design
  - [ ] Add mathematical expression GUI nodes
    - [x] Add ExpressionNode and ExpressionSlot class
      - [x] Make separate QLineEdits in math widgets (e.g., numerator/denominator, base/exponent)
    - [ ] Add fraction, pow, root, log widgets
    - [x] Add ParenNode to cover math expression
      - [x] Add draw object for each parentheses kind
    - [ ] Make toggleable for mathematical expressions (rawStr <-> rendered)
    - [ ] Test edge cases and add GUI tests
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
    - [ ] Flatpak
  - [ ] macOS packaging
    - [ ] .app bundle + dmg/zip distribution

- [ ] Tests (native core + pipeline)
  - [ ] Unit tests
    - [x] Native unit tests
      - [x] Native Calculator class tests
      - [x] Native Parser Unit tests: Tokinize, Normalize, Scanize, Shantinize
      - [x] ops.hpp tables tests: op_table flags/arity/symbol invariants
    - [x] Py Core unit tests
      - [x] Rpn eval
      - [x] Promotion rules
      - [x] Number tokens parse utils
      - [x] Error handling
      - [x] Native pybind tests
    - [ ] GUI unit tests
  - [x] E2E Edge cases / regression tests (add to golden list)
  - [ ] Performance tests
    - [x] Add benchmark tests
    - [ ] Add Malloc tests

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
