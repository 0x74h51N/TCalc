# Probe tools: one skeleton to look at a case layer by layer

Issue: #283. No milestone.

## Intent

Every bug and every precision question in TCalc is first looked at with a throwaway script. The scratchpads of past sessions hold 574 of them (431 Python, 143 C++, copies of repository files left out), and the same setup is written again in each: the editor round trip and `evaluate_branch`, a `ulps()` helper and an mpmath reference, an offscreen `QApplication` with isolated settings, a tree dump of the editor, a C++ `main` that reads rows from stdin and prints `%.17g`, a `chrono` loop. Part of every run goes to mistakes in that setup instead of to the case.

The probe tools are that setup, written once, so a case is looked at layer by layer with one command. Their job is to find the layer where a case goes wrong. Whether a case is right end to end is what the test suites already answer (`tests/py/e2e/test_eval_e2e.py`, `tests/py/e2e/ui/test_expression.py`); the tools do not repeat them.

## What the scratch probes did

Counted over the 574 scripts (2026-11-23), the number of files that use each thing:

- Eval: `tokenize` 78, `editor_canonical` or `evaluate_branch` 43, `format_result` 33, `clear_vars` 29, `tokens_to_flat_text` 25, `calc_native.apply` 24.
- Reference: mpmath 33, a hand written ulp count 23 (`cr.py`, `arms.py`, `p231/grade.py`); the same op run on the double and the BigReal arm side by side.
- Editor and render: the editor 47, the painter 29, the renderer and Math Widgets 13, the history item 19. The editor probes (`probe184*.py`, `probe_left.py`, `probe_cells.py`) all build an `Expression` offscreen, dump the slot tree with the cursor marked, call `navigate_left`, `backspace` or `apply_key`, and dump again.
- Window: a theme 151, `QApplication` 148, a screenshot 58, `MainWindow` 54, `QSettings` isolation 49.
- C++: the `Calculator` kernels 40, `eval.hpp` 16, `parser.hpp` 12, `cpp_dec_float` 25, `boost/math/tools/roots.hpp` 21, `cpp_complex` 14, `chrono` 46, random rows 19. The shape is always the same: rows on stdin, one value per line, a Python script that grades the lines against mpmath and compares two columns (old and new kernel).
- Rare: `shunting_yard` 2, `build_math_nodes` 1.

## Goals

- A Python command, `probe`, that shows a case on one layer of TCalc at a time: the whole Python path, the parser, the binding's `apply`, `format_result`, the editor, the renderer, the painter, and the window as a picture.
- A native command, `native_probe`, that runs the C++ layers without the binding: `literal_value`, `tokenize` with `normalize` and `shunting_yard`, the promotion steps (`promote_big`, `coerce`, `promote_complex`), the kernel alone (`ops::kernel_of`), `apply`, `evaluate`, and Boost's own functions with TCalc bypassed.
- A grader that both use: the expected value from python-flint and the error in ulps, or the residual for a BigReal.
- Any case a test suite holds can be run on these layers by its test id.
- A person who has not read the code uses them as easily as an assistant: one short command each, a help with examples, a doc that says which command answers which question, and output a person can read without the app open.
- The specifics the scratch probes wrote most are ready (below). A new specific probe is a small file on the skeleton, kept in the tree once it was needed.

## Non-goals

- No random sweep or generated inputs: that is #272's oracle, which uses the same grader.
- No driving the app through key sequences, menus or memory keys.
- No assertion of a right answer: the tools print, they do not pass or fail.
- Not part of `make py-test`, `make native-test`, the hooks or CI.

## Anti-goals

- A script that is long or tangled. Each command is a thin composition of existing functions; a command that grows a second job is split.
- A second copy of something TCalc has: op names come from the ops table (`find_op`), a native operand is built by its own type, the Python display text is `format_result`.
- An API added to `src/` only for the tools. If a layer cannot be reached, the spec of that probe names the missing API and the case that needs it, and the human agent decides.
- A double sneaking into an input: every input is text until the layer under test reads it.

## Constraints

- The rules in `docs/rules/ai/`: no em dash, typed and annotated Python under mypy strict, native code under `TCALC_WARNINGS`, named casts, no magic numbers, a closed set as an `enum class`.
- Values in the output and in this spec are in the flat op form (`(1e300)⌄3`, `(2)⁻¹`), as `docs/rules/ai/tests.md` writes them.
- python-flint becomes a dev dependency in `pyproject.toml` (the human agent agreed, 2026-11-23). mpmath was the first choice; it ships no types and has no stub package, and mypy strict is not silenced, so the typed python-flint (`py.typed`, the FLINT project's own binding) took its place. Measured 2026-11-23: it has every op TCalc has, reads a decimal text exactly through a fraction, and `float()` of a ball that fixes one double agreed with the correctly rounded `Fraction` on 20000 random fractions.
- Linux is what CI and development run; macOS is not measured (see Isolation).

## Approaches

For the native side three ways were weighed.

- A C++ executable linked to `calc_core`, with a fixed frame and a table of calls (chosen). It runs every layer at C++ speed, times in nanoseconds, and reaches internals the binding does not expose (`kernel_of`, `coerce`, the promotions). Cost: a build of a few seconds after a change to the table.
- cppyy, to call Boost and TCalc from Python without a build. Rejected: a heavy new dependency, and timings taken from Python are wrong for a kernel that runs in tens of nanoseconds.
- Binding the internals and Boost's alternatives into `calc_native`. Rejected: the production module would carry experiment code, against the rule of no API only for a script.

For Boost, wrapping every header and every function up front was rejected: Boost.Math alone has hundreds of functions over four number types, most of which would never be called. A Boost function is one row of a table, added when it is needed.

For isolation, the list of `monkeypatch.setattr` on each `QSettings` site that the UI fixtures repeat today was rejected in favor of Qt's own redirection, which covers every `QSettings("TCalc", "TCalc")` at once (seven sites in `src/`, one of them, `shortcut_manager.py`, patched by no fixture).

## Shared pieces

### Input text

An input is a string in the flat op form, given by the user of the tool at the moment of use. The tools hold no case, constant or shorthand of their own.

### Definitions

A value used by many cases is defined once, at the moment of use, and named in each input. `--def NAME=EXPR` (repeatable) and `--defs FILE` (one `NAME=EXPR` per line) define it; an input names it as `@NAME`. Before any layer reads an input, each `@NAME` is replaced by `(EXPR)`, so every layer sees the same text a user would type and the case is not changed by the substitution. A name that is used and not defined is an error that names it.

The marker is `@` because a bare name is a TCalc variable (`M` tokenizes to a `Char` token), and the substitution must never take a variable the case means. Substitution is text, not TCalc's own variable assignment, because a variable reference reaches the evaluator through `VarStore`, which is a different path from the literal the case is about.

Inputs come from the arguments or, with `-`, one per line from stdin, so a list of cases and one `--defs` file are run together.

`native_probe` has definitions of its own, and they are a different thing: a native operand is a typed value, not text, so a native definition is a typed value (`--def M=int:-9223372036854775808`, used as `@M` in an operand). The Python definition is expression text for the layers that read text. They share the `@NAME` marker and the `--def` and `--defs` spelling, nothing else.

### Value line

Every layer that produces a value prints one row in the same columns, under one header line, aligned for a person to read; the grader reads the same output, so there is one format:

```
input              layer    type     value
(1e300)⌄(3)        apply    float    9.999999999999872e+99
```

The input column holds what the layer actually read. For an expression it is the text after the definitions are substituted. For typed operands (`native_probe`, and the op alone in `probe layers`) it is the op and each operand as it is held, exactly: a double as its hexadecimal form (`%a`), a `Rational` as `p/q`, a `BigReal` at its full digits. A double operand written by its short text would be read back by the grader as another number (`0.1` is not the double nearest 0.1).

The type is written with the type names the e2e table in `tests/py/e2e/test_eval_e2e.py` and the PR tables already use: `int`, `float`, `complex`, `Rational`, `BigReal`, `BigComplex`, `Collection` (one per `tcalc::Value` arm, `Arm` in `value.hpp`). The value text: a double as its shortest round trip text, a `Rational` as `p/q`. A double is written as Python's `repr` writes it, a complex as Python's complex `repr`, on both sides, so a Python row and a native row of one case read the same. A `BigReal` or `BigComplex` is written by `decimal_text(value, 0)` on both sides: Boost's `str(0)` writes the digits the value holds, so the text reads back to the same value (measured 2026-11-23: `1/3` in BigReal gives 72 digits, and `apply(Sub)` of the value and that text is `0`). `repr` is not used; it writes 16 digits (`kPythonPrecision`). A BigReal is still graded by its residual (below). An error prints its class and its message in place of the value, as the Python side prints it.

### Grader

`--ref` on any command adds the expected value and the error to each value row. There are two expected values, and the input column decides which one a row gets, so no flag chooses:

- An expression row is graded against the mathematical value of its text: `0.1` is one tenth. This is the PR tables' Expected column, the value a user means.
- A typed operand row is graded against the exact result on the operands as held: `dbl:0.1` is the double nearest one tenth. This is what tells whether a kernel rounds correctly.

The expected value is a python-flint ball (`acb`, a real one has an exact zero imaginary part) at 80 digits: a value with a guaranteed error radius. When the ends of the ball round to the same double, that double is the correctly rounded expected value; when they do not, the line says the reference does not fix a double instead of giving an error. A double result is graded in ulps against the correctly rounded double, each part of a complex number on its own. A `BigReal` result is graded the way the findings measured it (`real-root.md`, `combinatorics.md`, `arms.py`): the exact value is written by python-flint as text, built as a `BigReal`, and subtracted from the result with TCalc's own `Sub` (`calc_native.apply`); the residual and the error relative to the exact value are printed. No digit count is needed for that. A `BigReal` line from `native_probe` is graded on its full text against python-flint. The grader does not parse an input itself. A typed operand row gives it the op and the operands directly. For an expression row it walks TCalc's own RPN (`calc_native.tokenize_string`, `calc_native.shunting_yard`, the paren and call tokens descended into) with one python-flint function per `OpId`. That table is the grader's one table, one row per op, and it states TCalc's meaning where python-flint's differs (the real-first odd root, which python-flint gives as `nan` on a negative real or as the principal complex root); an op with no row is reported as not graded.

`probe grade FILE [FILE]` grades value lines read from a file or stdin (the output of `native_probe`, for one). With two files it lines the rows up by input and counts, per file, the ulp histogram, and between them how many rows got better and how many got worse: the `p231/grade.py` comparison.

### Isolation

One function, `isolate_app(folder)`, makes a `QApplication` safe to open the real windows in: `QSettings.setPath(NativeFormat, UserScope, folder/config)` redirects every `QSettings("TCalc", "TCalc")`, `XDG_DATA_HOME=folder/data` moves `history.dat`, and the `AppState` singleton is reset so it binds to the new settings. Both were seen to work mid process (probe of 2026-11-23: after `setPath`, `QSettings("TCalc","TCalc").fileName()` is under the folder; after the variable, `AppDataLocation` is). XDG variables are not read on macOS; that is not measured and not handled.

It lives in `tests/py/helpers.py`, beside `editor_canonical`, and the UI fixtures that build a `MainWindow` (`test_view_state_ui_sync.py`, `test_theme_switch.py`) call it instead of their own `monkeypatch` lists. That change is a relocation: no new test, the existing suite staying green is the check.

## Python: `probe`

`scripts/probe <command> ...` (new file, a short shell script like `scripts/dev`) runs it with the `.venv` interpreter and `PYTHONPATH=src:<repo root>`, from any directory, with no quoting through make. The `.venv` interpreter is required: the system `python` carries another PySide6 and behaves differently (`docs/superpowers/findings/ui-test-isolation.md`).

The code is a package, `scripts/probes/` (new directory): `__main__.py` holds the command table, one row per command (name, module, one line of help, one example), and each command is one module with one function. A new specific probe is a new module and a new row. Each command takes one or more inputs and prints for each. `scripts/probes` is added to `files` in `[tool.mypy]`, so it is checked under `strict` like `src` and `scripts/stubgen`.

`scripts/probe` with no command lists the commands, each with its line of help and its example; `scripts/probe <command> --help` gives the command's options and at least one example a person can paste. Inputs may use the ASCII aliases the tokenizer already reads (`(2) root (3)` is `(2)⌄(3)`), and the help names them, since `⌄` and `⁻¹` cannot be typed on a keyboard.

Eval side:

- `probe eval INPUT...`: the whole Python path. The editor's plain text (`editor_canonical`), `tokenize`, `evaluate_branch` with a fresh `Calculator` and `clear_vars`, the value line, the display text (`format_result(value, group=True)`), the text written back into the editor (`format_result(value)`), and whether that text evaluates back to the same value. Same value means the same type and the same exact text: `==` on a bound type compares identity, not value (`Rational(1,3) == Rational(2,6)` and `BigReal('2') == BigReal('2')` are both `False`, measured 2026-11-23).
- `probe layers INPUT...`: the same case on each layer, one block per input, in the order `docs/rules/ai/tests.md` asks for: the tokens with their kind and op id, and their flat text (`tokens_to_flat_text`); the RPN order (`shunting_yard`); the render tree (`build_math_nodes`, `structural_split`) when the input has a LaTeX token; the binding path without the editor (`calc_native.evaluate`); the op alone through the binding (`calc_native.apply`, its operands each evaluated on their own, read from the last op of the RPN, from a call token's `args`, or from a LaTeX token's `op_id`, `left` and `right`); `format_result` of each value. The native layers without the binding are `native_probe`'s (below), run on their own.

Editor and render side. Each runs offscreen on settings and history of a temporary folder (`isolate_app`), so the user's own are never read or written.

- `probe editor INPUT... [--step STEP...]`: the app's own window (`MainWindow`), the text set in its editor, then each step as the user does it: `left`, `right`, `up`, `down` and `bs` as key events through the app's keyboard handler, `key:NAME` through `controller.handle_key(op.symbol, op)` with `op = Operation[NAME]`, `text:TEXT` typed with `QTest.keyClicks`. The slot tree with the cursor marked and the plain text are printed after each. The tree comes from `tcalc.debug.snapshot_slot`, one line per row: `'' Fraction<'1' ; '2|'> ''`. `@NAME` is substituted as typed, without parentheses.
- `probe render INPUT`: the renderer alone, without the editor's key handling. `MathRender(read_only=True).render_node` on a fresh `ExpressionSlot`'s field with the tokens of INPUT, then the same tree. The read only renderer is the result line's path (`result.py`); the editor's own renderer is the one `probe editor` reaches. `render_node` catches every exception and only logs it at debug level, so the probe turns on debug logging for `tcalc.ui` and a failure inside the renderer is printed, not lost.
- `probe paint INPUT`: the painter alone, the path history uses. The default theme is loaded first, and the font is the one `HistoryItem._math_paint` builds (the app font at `get_theme().look.history.math_font_size`). Then `MathPainter().paint_tree(tokenize(INPUT), font)`, and each layout box after measure and place: its type, `x`, `y`, `w`, `h`, `above`, `below` and, for a text leaf, its text.
- `probe shot TEXT... --png FILE [--size WxH] [--theme NAME]`: the whole window with each text typed in, a fresh window per text, and what the editor and the result line show; the last one saved as a picture.

`--png FILE` on `editor`, `render` and `paint` saves a picture of what was printed, by `QWidget.grab()`, and `--theme NAME` styles all four. A Math Widget alone has no command: `render` reaches each through the renderer.

## Native: `native_probe`

A CMake executable, `native_probe`, in `src/native/tools/probe/` (new directory), linked to `calc_core` and built with `TCALC_WARNINGS`. It is `EXCLUDE_FROM_ALL`: `make native-build` and `make native-test` do not build it; `make native-probe` does. `scripts/native_probe <command> ...` (new file, a short shell script) runs its ninja target (a no-op when nothing changed, a rebuild when the tool or the core did), then runs it, so a person never looks for the binary in the build directory. It reads its inputs from the arguments or, with `-`, one per line from stdin, and prints value rows. With no command it lists the commands with an example each, and `--help` on a command gives its options and an example, as `scripts/probe` does.

The frame, written once (`frame.hpp`): read an operand as a typed value, `TYPE:TEXT`, built by the type itself with no tokenizer and no evaluator in the way: `int:` by `std::from_chars` into `std::int64_t`, `dbl:` by `std::from_chars` into `double` (correctly rounded), `rat:P/Q` as `Rational(p, q)` from two `from_chars` integers, `big:` by `BigReal(text)`, `cx:RE,IM` from two doubles, `bigcx:` in `decimal_text`'s form (`RE+IMi`, `IMi`, `RE`), the only one the binding can write. A collection operand (`list:`) is written by the Python side but not read here; no case has needed it. A text a type cannot hold whole (an int past int64, a malformed part) is an error that names the operand. Write the value line, and time a call with `--time N` (N runs, the median per call in nanoseconds, the result kept alive so the loop is not removed). An op is named by its symbol or alias and found with `ops::find_op`, so `⌄`, `root` and `^` all work and no name table is added.

Commands, one function each, in a command table in `main.cpp`:

- `literal TEXT...`: `literal_value`. Which arm a literal lands on and its exact value.
- `tokens EXPR`: `tokenize`, then `normalize`, then `shunting_yard`, each as a list of token texts.
- `promote OP ARG...`: the steps `apply` takes before the kernel, each with the arms after it: `promote_big`, `coerce`, `promote_complex`, `coerce` again when the promotion changed something. The real-first rewrite of a root or a power, which apply runs before these, is not shown (`findings/probe-tools.md`).
- `kernel OP ARG...`: `ops::kernel_of(id)` on the typed operands as given, with no ladder, no real-first rewrite and no retry: what the kernel alone gives on that arm. The kernel dispatches on its first operand and expects every operand on that arm, as `coerce` leaves them, so operands of different types, or an arm the op does not accept (`ops::arms_of(id)`), are an error that names the types before the kernel is called.
- `apply OP ARG...`: `eval::apply`, the whole ladder.
- `eval EXPR [--no-closed-forms]`: `tokenize` and `evaluate`, the native end to end path without the binding.
- `boost NAME TYPE ARG...`: a Boost function, TCalc bypassed. NAME is a row of the Boost table (`boost_table.cpp`): the name and one lambda generic over the number type. TYPE is `double`, `long double`, `dec50` (`cpp_dec_float_50`, TCalc's `BigReal`) or `bin` (`cpp_bin_float_100`). The spec fixes only the shape of a row; the table holds no row in advance, and a row is added by the investigation that first needs that Boost function, then kept.

`--arms` on `kernel` runs the same op on every arm the kernel accepts (`ops::arms_of(id)`), each operand lifted with the helpers in `value.hpp` (`to_double`, `to_complex`, `to_big`, `to_big_complex`, `to_rational`), one value line each, and a line saying so for an arm the operand has no lift to: the double against BigReal comparison `arms.py` made by hand.

## Cases from the test suites

A case a test already holds is run by naming the test, not by copying its input.

Python tests: `--test NODEID` on any `probe` command, where NODEID is pytest's own node id (`tests/py/e2e/test_eval_e2e.py::test_eval[precedence-mul-over-add]`), and `--test FILE -k EXPR` for every row pytest's `-k` selects. The probe runs pytest's collection in process (`pytest.main` with `--collect-only` and a plugin that keeps the collected items) and reads each item's `callspec.params`, so every parametrized test in `tests/py` is reached the same way and no name table is kept. Tests name their params differently (`expr`, `case`, `expr_case`, `rendered_case`, and dataclass rows whose input is a field, `RootCase.expr`), so `--field PATH` names the input (`--field expr`, `--field case.expr`); without it the probe prints the row's fields and runs nothing. The row's other fields (the expected value, the type) are printed beside the probe's output, so the test's claim and each layer's result are read together. An id that collects nothing, or a field path the row does not have, is an error that names it.

Native tests: their rows live inside the test functions and run through `test_detail::with_case` (`TEST_CASE`), so they are not data that can be read from outside. The existing runner is extended instead: `native_tests --case ID` runs only the cases whose id path starts with ID, the path a failure line prints with its suite first (`--case "unit test helpers :: print :: integer"`), with `-v` for their output. An ID that matches no case is an error, not a green run. No case in the tree nests another, so no case runs on the way to ID. The filter sits in `with_case`, the one place every case passes through, and the argument is read in the existing loop in `tests/main.cpp`. Looking at such a case layer by layer is then `native_probe` on its operands.

## The specifics made ready

From what the scratch probes wrote most:

- The ulp count against the correctly rounded double, and the residual for a BigReal (`--ref`).
- A case taken from a test by its id (`--test`, `native_tests --case`).
- The same op on each arm (`native_probe kernel --arms`).
- The old against new comparison of two runs (`probe grade A B`).
- The nanosecond timing (`native_probe --time`).
- The editor slot tree with the cursor, and the steps on it (`probe editor`).
- A window picture with isolated settings (`probe shot`), and `--png` on the editor, render and paint commands.

A later need, such as measuring each segment's anchor and margin for `ExpressionSlot._update_segment_margins`, is written then as one more module in `scripts/probes/` (or one more command in `native_probe`) on the same frame, and kept.

## Tests

The tools print and assert nothing, and they get no unit tests: a test script is checked end to end, by running it. The Python tools are tested in `tests/py/e2e/test_probes_e2e.py` (and `tests/py/e2e/ui/` for the UI commands), through `scripts/probe`'s own `main` on the real binding; the native probe by running `native_probe` on its commands, with no test of its own (human agent, 2026-11-23). The grader's numbers go into PR tables as the expected value, so the e2e table holds a row for each row of the op meaning table, the ulp count, the BigReal residual, the choice between the two expected values, the definition substitution, the field path read from a test row and the two run comparison, each through the command. The slot tree dump gets one e2e test on a known editor tree, the paint and shot commands one each, and `--test` one on a row of `test_eval_e2e.py`. The native `--case` filter gets a row in the runner's own helper tests (`tests/test_test_helpers.cpp`), since `native_tests` is the runner itself.

## Docs

- `docs/probe.md` (new file): for people as much as for assistants. Which question goes to which command (a wrong value, a wrong type, a lost digit, a wrong render, a misplaced cursor), where each command lives and which API it calls, one pasteable example per command, the typed operand forms, the definitions, `--test` and `--case`, how to read a value row and a graded row, a section for AI agents, and the rule that a missing command is written into the tools and documented there. `docs/dev.md` and `docs/CONTRIBUTING.md` link it, and `scripts/probes/` and `src/native/tools/probe/` each get a short `CLAUDE.md` that names it.
- `CLAUDE.md` (Commands) and `docs/dev.md`: `scripts/probe` and `scripts/native_probe`, one line each.
- `docs/rules/ai/tests.md` and `docs/rules/ai/efficiency.md`: a case is first looked at with the probe tools, a new probe goes on their skeleton and stays; a throwaway script is written only for what the skeleton cannot reach, and the finding says why.
- `docs/superpowers/findings/`: entries name the probe command they ran, copy-paste ready.

## Left to the builder

- The wording of the help lines and of the block headings, within what the help section above requires.
- Column widths of the value rows.
- The grader's op meaning table: one row per op the tests reach, written from `docs/glossary.md` and the op's kernel, with the ops that cannot be graded named.
