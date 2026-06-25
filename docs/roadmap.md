# Release Plans

Goal: ship a stable v1 with a polished UI/UX and a solid native core.

## v1 Roadmap

### Input / Parser / Eval

---

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
- [x] Add collection
  - [x] Parser
    - [x] Replace open/close pair token model with unified ParenToken containers
      - [x] Unify grouped-expression tokenization into first-class ParenToken containers
      - [x] Allow each element to store a Token or a token list (operations, latex, nested paren groups, etc.) <br>
            `ParenElement = std::variant<Token, std::vector<Token>>;`
      - [x] Parse round / square / curly spans as container tokens
      - [x] Preserve open / close / stray-close cases during tokenization
    - [x] Split top-level comma-separated elements into independent token trees
    - [x] Adapt structural_split and build_math_nodes to ParenToken elements
      - [x] Cascade ParenSplit vs LatexSplit per element based on has_latex_descendant
      - [x] Cache has_latex_descendant bottom-up on each ParenToken
    - [x] Add ParenElement single-token shortcut / SBO storage
  - [x] Bindings (pybind)
    - [x] Expose ParenKind / ParenToken / ParenElement to Python
    - [x] Pickle support for ParenToken (state restore + history persistence)
    - [x] Token element iteration helper for Python-side traversal
  - [x] Evaluation
    - [x] Canonicalization
      - [x] Scalar canonicalization: bypass shunting-yard and RPN for single-token elements
      - [x] Type canonicalization: Rational -> primitive types where exact
    - [x] Route multi-token elements through shunting-yard and RPN evaluation
    - [x] Add Collection runtime value
      - [x] Evaluate ParenToken elements independently when element count > 1
      - [x] Move List / Point classification to the eval layer from ParenToken type
  - [x] Tests
    - [x] Add native and Python regression coverage (tokenize, structural_split, build_math_nodes, eval scalar/multi-element)
- [x] Add function-call paren (CallToken)
  - [x] Parser
    - [x] Tokenize a `(` right after a call-function as a CallToken `{op_id, args}` (O(1) look-back peek via OpSpec CallFunction flag), not a grouping ParenToken
    - [x] Reuse ParenToken machinery (shared `build_paren_elements` comma-split, `ParenElement` storage, `_eval_elements`); split is semantic, not a parallel implementation
    - [x] Add `OpSpec.call_arity` (default 1; `kVariadicArity` sentinel) + `is_variadic()`
  - [x] Evaluation (single dispatch keyed off `call_arity`)
    - [x] Variadic ops (reducers, gcd, lcm): collapse call args into one `Collection(List)` dataset and fold; `x̄(2,3,5,6)` == `x̄[2,3,5,6]` == `x̄([2,3,5,6])`
    - [x] Fixed-arity ops: validate arg count, reject collection args, dispatch `func(*args)`
  - [x] Convert existing functions onto the call model
  - [x] Render
    - [x] classify-time lowering: CallToken -> `Op(symbol) + Paren(args)` (symbol as prefix TextNode, LaTeX args render structurally)
    - [x] `has_call` flag + `has_latex_descendant` propagation; `token_flat_text` flattens calls for history flat view
  - [x] Tests (native tokenize/number_theory, py e2e variadic + fixed-arity + arg-type errors, controller status surfacing, call render node cases)
- [x] Undo/redo integrates with history navigation (rebuild expression from previous calc and auto-eval)
- [x] Test edge cases
- [x] Add Rational support
  - [x] Extend ops with rational arithmetic (add, sub, mul, div, pow, root)
  - [x] Toggle any result between decimal and fraction view
  - [x] Keep results exact whenever possible, fall back to high-precision BigReal or float on overflow
  - [x] Resolve fractional exponents exactly when the result is a clean integer or fraction
- [ ] Add line-based calculation
  <!-- GUI form = the new Advanced calc mode (sheet/tab, stacked editable lines, per-sheet env,
       history panel deactivated, tabs persist + lazy per-tab render/eval).-->
  - [ ] Add row-based expression model (one expression per line)
  - [ ] Allow referencing previous lines / session values
  - [ ] ANS / previous-result reference
  - [ ] Per-line eval with a per-sheet variable store (env per sheet/tab, no cross-sheet visibility)
  - [ ] Keep line evaluation isolated so one failed line does not break others
  - [ ] Add line actions (insert, remove, duplicate, reorder)
  - [ ] Allow Collection values in row references
- [x] Add variable assignment, parser -> eval
  - [x] Parse assignments (`=` operator + single-letter `CharToken`)
  - [x] Add variable store for current session (`VarStore`, stored as-is, native-typed)
  - [x] Allow assigned variables in other lines (env threaded through eval)
  - [x] Define overwrite / invalid-name / undefined-variable behavior
- [x] Add native constant table matched at tokenize (`ConstToken`)
  - [x] Declarative `ConstId`/`ConstSpec`/`kConstants` (value native-sourced, `variant<double, Complex>`)
  - [x] `match_const` longest-match before the `CharToken` splitter (fixes multi-char constants splitting)
  - [x] Eval resolves value by `ConstId` from native `const_table()` (single source; `constants.py` derived)
  - [x] Reject assignment to a constant
  - [x] Constants grouped by category
    - [x] Mathematics: π, e, i, φ, τ
    - [x] Universal: c, h, ℏ, G
    - [x] Electromagnetism: ε₀, μ₀, Z₀, ᵉ
    - [x] Atomic & Nuclear: α, a₀, R∞, mₑ, mₚ, mₙ
    - [x] Thermodynamics: R, k
    - [x] Chemistry: Nₐ, F, mᵤ
    - [ ] Deferred: b_W, R_K, K_J, μ_B, μ_N (depends on variable index rendering, e.g. b\_{W})
- [ ] Add user-defined (custom) functions
  - [ ] Parse function definitions (`f(x) = expr`)
  - [ ] Bind named user functions in the session store; call them like built-ins
- [ ] Add piecewise expressions (`{ cond: value, ... }`)
  - [ ] Relational / boolean conditions (`>`, `<`, `>=`, `==`, `!=`)
  - [ ] Branch evaluation: first matching condition wins; undefined when none match
  - [ ] Piecewise math-render widget (brace with condition / value rows)
  - [ ] Depends on variables + custom functions

### Error handling & messages

---

- [x] Error mapping spec (engine -> UI: Invalid / Malformed / Math Error kinds)
- [x] Centralize user-facing message text in single-source tables
  - [x] Native `tcalc::errmsg` table (call-function + collection input-type messages)
  - [x] Python `Msg` table (parser + controller message strings)
  - [x] Controller surfaces Math Error / Invalid detail in the status line (short kind in result; Malformed stays generic)
- [ ] Move ALL remaining engine error messages onto the tables

### Calculus

---

#### Scientific

- [x] UI / Controls
  - [x] Science keypad panel
  - [x] Angle unit radios (Deg/Rad/Grad) - state/binding
  - [x] Shift toggles and shift keys
- [x] Trigonometry
  - [x] sin/cos/tan (angle-aware)
  - [x] Hyp toggle and hyperbolic keys (sinh/cosh/tanh)
  - [x] inverse trig via Shift (asin/acos/atan or asinh/acosh/atanh)
- [x] Basic Science Functions
  - [x] Logarithmic & Reciprocal
    - [x] log10, ln
    - [ ] Logarithm with custom base - log(x, base)
    - [x] 1/x
  - [x] Combinatorics - x! (factorial), nPr (permutation), nCr (combination)
  - [x] Number theory - gcd, lcm, mod, intdiv
- [x] Power / Complex - sqrt, x², xʸ, i, complex domain rules
- [ ] Iterated ops - summation (Σ), product (Π) over a bound variable and range
- [x] Parser parity - Implement ops in native + pybind
- [x] Edge cases + error messages

#### Statistic

- [ ] Data store built on Collection (variable-bound mutable native buffer; freeze-on-share; ValueOperand resolution; draft design'd)
  - [ ] Add / remove / edit(i) / clear data points (in-place on the mutable buffer)
  - [ ] Mutation-line result: bounded preview + element count (size-capped)
  - [ ] Optional dataset persistence toggle (def false)
- [ ] CSV collection load
  - [ ] Native fast-path: build Collection directly from CSV stream, bypass the tokenize -> shunting-yard -> eval pipeline (`Collection.from_csv()`)
  - [ ] Multi-column ingest: each column becomes its own Collection, bound to a user-named variable
  - [ ] Load UX
    - [ ] File picker + delimiter/header inference
    - [ ] Column preview with type detection
    - [ ] Missing-value detection during load
    - [ ] Imputation strategy per column (mean, median, nearest-neighbor, constant, drop row)
    - [ ] Preview imputed vs original side-by-side before commit
  - [ ] Edge cases + error messages (malformed rows, mixed types, encoding)
- [ ] Data normalization / preprocessing
  - [ ] Per-column transform pipeline (chainable, preview before commit)
  - [ ] Scaling
    - [ ] Min-max (configurable target range, default 0..1)
    - [ ] Z-score standardization (mean=0, std=1)
  - [ ] Log / log1p transform (for skewed distributions)
  - [ ] Outlier handling (IQR or z-score detection, clip / drop)
  - [ ] Persist applied pipeline on the Collection (reproducibility + inverse transform)
- [ ] Data panel UI
  - [ ] Show dataset list + summary (n, Σx, Σx²)
  - [ ] Show dataset change log (added/removed/cleared)
- [ ] Keypad integration (left panel)
  - [ ] Statistic operations as buttons (mean, median, min, max)
  - [ ] variance + standard deviation (sample vs population)
  - [ ] Shift toggles secondary operations (Σx, Σx², etc.)
- [ ] Implement ops in native
  - [ ] Aggregation
    - [x] Basic: mean, median, min, max, variance, stddev (sample & population)
    - [ ] Percentile / quantile (Q1, Q3, configurable p)
    - [ ] Mode, range (max - min), count of unique values
  - [ ] Sort / filter / select
    - [ ] Ascending / descending sort
    - [ ] Filter by predicate (`> x`, `< x`, `between(a, b)`, `== x`)
    - [ ] Random `sample(n)` (bootstrap-friendly)
  - [ ] Pairwise / two-collection
    - [ ] Pearson correlation, covariance
    - [ ] Simple linear regression (slope, intercept, R²)
  - [ ] Add pybind bindings
  - [ ] Add input-type validation and regression tests
  - [ ] Ensure parser maps symbols / aliases correctly
- [ ] Edge cases + error messages

### Menubar

---

- [x] File menu
- [x] Edit menu (undo, redo, cut, copy, paste), binding/apply
- [x] Constant menu
  - [x] Add constants grouped by category
- [ ] Help menu
  - [ ] Find Action
  - [ ] User manual
  - [ ] About, vers, licance etc.
- [ ] Settings menu
  - [ ] Configure TCalc
    - [ ] General conf
      - [ ] Max number of digits, precision
      - [ ] Math render mode settings
        - [ ] Per-expression render policy toggles (fraction, root, etc.)
    - [ ] Fonts
    - [ ] Themes
    - [ ] Constants
  - [ ] Configure keyboard shortcuts
  - [ ] Calc Modes
      <!-- A real mode, not a keypad layout; separate from the keypad-preset/dock buttons
          the View menu item moves out of Settings. -->
    - [ ] Simple
      - [ ] Add button + handler with global state
      - [ ] Keep the history panel, single-line calc/display, and keypads (positions + active/hidden)
      - [ ] Local persistence - pads (positions + active/hidd)
    - [ ] Advanced
      - [ ] Add button + handler with global state
      - [ ] Disable the history panel; do not add/persistance calculations to it
      - [ ] Disable memory buttons (M+/MR/MC/MS) + feature
      - [ ] Activate the sheet/tab calc/display view
      - [ ] Make "=" keypad button operation Ops::Assign
    - [ ] Local persistence last selected mod state

- [ ] View menu
  - [ ] Add this menu
  - [x] Dock window toggle buttons
    <!-- TODO: buttons work but still live under the Settings menu in code; move them to this View menu -->
    - [x] Keypad Presets (basic, scientific, statistic)
    - [x] Keypads
      - [x] All keypads
      - [x] Custom keypads toggles and Add Custom Pad button
      - [x] Constant pad toggle
    - [x] History panel toggle
    - [x] Restore keypads layout style
  - [ ] Add constants' keypad toggle buttons

### History panel

---

- [x] Add history panel with open/close shortcut
- [x] Make separate history for calc modes
- [x] Make history items design more pleasant and add copy icon (auto copy -> copy icon)
- [ ] Make max history item count configurable in general settings
- [x] Make human readable history items formatter (LaTeX -> math symbols)
- [ ] Allow disabling history persistence (local storage) via settings
- [ ] Export as text file

### Keyboard shortcuts

---

- [x] Basic shortcuts and handlers (cut, copy, undo, redo, quit etc.)
- [ ] Configurable shortcuts, bind/apply via a configuration window

### GUI / UX / Accessibility

---

- [x] Memory for all modes MS, MC, MR, M+ Buttons
- [ ] Improve styles and layout design
  - [x] Add dock layout
  - [x] Split keypads (e.g. num, func, etc.) into dock widgets
  - [ ] Add custom pad
    - [x] Allow creating multiple custom pads
    - [x] Operation key assignment
    - [ ] Constant key assignment
    - [x] Custom grid layout
    - [x] Add edit mode and persist changes on exit
    - [x] Add context menu
      - [x] Rename or remove custom pad
      - [x] Add customizable background and text colors
      - [x] Add option to remove or change key operation
- [ ] Keypad layout presets (preset dock/keypad layouts; keypads are dock-composable)
  - [x] Layout state, layout update, binding and side effects
  - [ ] Basic preset: simpler-operations keypad dock layout
  - [ ] Scientific preset: sci-fi / advanced-operations keypad dock layout
  - [ ] Statistic preset: data-store + statistic-operations keypad dock layout
- [ ] Add mathematical expression GUI nodes (math render)
  - [x] Add ExpressionNode and ExpressionSlot class
    - [x] Make separate QLineEdits in math widgets (e.g., numerator/denominator, base/exponent)
  - [ ] Add fraction, pow, root, log, summation, product widgets
  - [ ] Add absolute value `|x|` and floor/ceil `⌊x⌋` `⌈x⌉` widgets
  - [ ] Add variable indexing (variable node w/subscript e.g. x\_{0} -> x₀)
  - [x] Add ParenNode to cover math expression
    - [x] Add draw object for each parentheses kind
  - [ ] Make toggleable for mathematical expressions (rawStr <-> rendered)
  - [ ] Add selective render mode in main display
  - [ ] Test edge cases and add GUI tests
- [ ] Sheet calc/display (Advanced-mode line-based view)
  - [ ] Stacked editable lines: one expression per line; each renders via the expression.py editor pipeline and evaluates independently (parser.py) with the sheet's env; result shown inline per line
  - [ ] Each sheet holds its own variables (per-sheet env; no cross-sheet visibility)
  - [ ] Each sheet is persisted (tabs + their lines saved; restored on startup with lazy per-tab render/eval)
  - [ ] Sheets switchable via dock layout (tabs as dock widgets; optional side-by-side)
  - [ ] Default / app opening: always tab view with a single sheet (restore as tabs, not windows, to avoid first-load lag)
- [x] Collection GUI and Migration
  - [x] Migrate
    - [x] ParenWidget API to (kind, has_open, has_close) flags
    - [x] Render pipeline (math_render, expression_node) to unified ParenToken
  - [x] Comma input handling for collection element entry in the editor
  - [x] Add collection result rendering
    - [x] Show collection info text on result (`status_label`: "N element list / point" while typing)
    - [x] Add invalid input error handling and messages (user-friendly hint for bare comma outside any paren)
    - [x] Show collection elements with comma + whitespace
- [ ] Tab order + focus behavior
- [ ] High-DPI/font scaling sanity pass
- [ ] Basic tooltips for all keys

### Packaging

---

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

## v2 Roadmap

### Science calc improvements

---

- [ ] Calculus (numeric)
  - [ ] Derivative (numeric)
    - [ ] `d/dx` at a point: `f'(a)` (auto step size)
    - [ ] Add derivative expression widget (`d/dx` math render)
  - [ ] Definite integral (numeric)
    - [ ] `int_a^b f(x) dx` (choose method: Simpson / adaptive Simpson)
    - [ ] Handle invalid ranges / discontinuities with clear errors
    - [ ] Add integral expression widget (`∫_a^b f dx` math render)
  - [ ] Limit (numeric)
    - [ ] `lim x->a f(x)` with side options: both / left / right
    - [ ] Detect non-convergence / undefined cases and show proper error
    - [ ] Add limit expression widget (`lim_{x→a}` math render)
- [ ] Add vector and operations
  - [ ] Add vector input and typed eval (Scalar or Vector)
  - [ ] Rules: `s*v` / `v*s` scales, `v+v` / `v-v` only if same dimension, `v/s` ok, `v+s` and `v*v` invalid
  - [ ] Add vector functions `dot(v,w)`, `cross(v,w)`, `length(v)`, `normalize(v)`, `angle(v,w)` -> scalar
  - [ ] Add vector expression widget (column/row math render)
- [ ] Add matrix and operations
  - [ ] Add matrix input and typed eval (Scalar, Vector, Matrix)
  - [ ] Rules: `A+B` same shape, `A*B` multiply, `A*s` scale, `A^T`, `det(A)`, `inv(A)`
  - [ ] Add matrix functions `trace(A)`, `rank(A)`
  - [ ] Add matrix expression widget (m×n grid math render)

### Programmer Mode (Numeral system)

---

- [ ] Binary input and output
- [ ] Hex, dec, oct, bin modes
- [ ] Logical and bit operations
- [ ] Bit width + signed/unsigned (8/16/32/64) and overflow behavior
- [ ] Bitwise shifts, rotate
- [ ] Two's complement display for negatives (define the rule)

### Graphic Mode

---

- [ ] Graphic drawing to equations or calculations
- [ ] Graph screen and axes with inf length
- [ ] Function input + domain/range + sampling step (perf/quality knob)
- [ ] Zoom/pan + reset view
- [ ] Discontinuity handling (break lines at asymptotes)

### Localization

---

- [ ] Locale-aware decimal separator + formatting & input (comma/dot)
- [ ] Thousands separator formatting (space/comma/dot) and copy behavior
