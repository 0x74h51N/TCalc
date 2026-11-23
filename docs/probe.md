# Probe tools

Two commands look at one TCalc case on one layer at a time, so the first layer that goes wrong is seen instead of guessed: `scripts/probe` for the Python side and the UI, `scripts/native_probe` for the C++ layers without the binding. They hold no cases: a case comes from the command line, from stdin (`-`, one per line), or from a row of a test suite. Each prints the same aligned table, so any table can be piped into `scripts/probe grade`.

`scripts/probe` with no command lists its commands with an example each; `scripts/native_probe` does the same. `COMMAND --help` gives a command's options; a flag the command does not read is rejected.

## Which command answers which question

- A wrong value: `probe eval`, then `probe layers` (the binding, then the last op alone), then `native_probe apply`, `native_probe promote` and `native_probe kernel`. The first row that is wrong names the layer.
- A wrong type (a `float` where a `Rational` was expected): `native_probe promote`, which shows the operands after each of apply's promotion steps.
- A lost digit: `--ref` on any value table, or `probe grade` on a saved one.
- The same op on each arm (double, complex, BigReal, BigComplex, Rational): `native_probe kernel --arms`.
- Boost's own result, with TCalc bypassed: `native_probe boost`, after adding the function's row to `kBoostRows` in `src/native/tools/probe/boost_table.cpp`.
- A wrong render: `probe render` (the result line), `probe paint` (a history item in math mode).
- A misplaced cursor or a key that does the wrong thing: `probe editor` with `--step`.
- How it looks: `probe shot`, and `--png` on `editor`, `render` and `paint`.
- One native test case: `native_tests --case ID`.

## Reading a row

Every table has the columns `input`, `layer`, `type` and `value`, then the extra columns its rows carry. `input` is what the layer read: the expression after the definitions are substituted, or the op and its operands as they are held. `type` is the Python type name (`int`, `float`, `complex`, `Rational`, `BigReal`, `BigComplex`, `Collection`), `str` for a text, or the error's class. A value row has a `unit` column, the angle unit it was computed in (`--unit`, default `DEG`, the app's start unit).

With `--ref` (or through `probe grade`) a value row gets `expected` and `error`: the value python-flint computes for the same input, and the error as ulps for a double, `exact` for an exact value, the residual for a BigReal. A BigComplex is not graded (`not graded`).

```
$ scripts/probe eval "1/3" "sin(30)" --ref
input                   layer       type      value                           unit  expected  error
1/3                     editor      str       1 ÷ 3
1 ÷ 3                   eval        Rational  1/3                             DEG   1/3       exact
1 ÷ 3                   display     str       0.33333333333333333333
1 ÷ 3                   written     str       0.33333333333333333333
0.33333333333333333333  round trip  str       BigReal 0.33333333333333333333
sin(30)                 editor      str       sin(30)
sin(30)                 eval        Rational  1/2                             DEG   0.5       exact
sin(30)                 display     str       0.5
sin(30)                 written     str       0.5
0.5                     round trip  str       same
```

## scripts/probe

- `eval INPUT...`: the case through the whole Python path as the app evaluates it: the editor's text, the value, the result line's text, the written text and whether that text reads back to the same value.
- `layers INPUT...`: the tokens, the flat text, the RPN, the render tree, the binding, and the last op alone through `calc_native.apply` with its operands in the typed form `native_probe` reads. The op alone skips the op's exact rule, so `sin(π)` with `--unit RAD` is `Rational 0/1` on the binding row and `1.2246467991473532e-16` on the apply row: that split is the exact rule, not a bug.
- `editor TEXT... --step STEP...`: the text in the app's editor, then each step (`left`, `right`, `up`, `down`, `bs`, `key:NAME` for an `Operation` member name, `key:SQRT`, `text:TEXT` typed): the widget tree and the cursor `|` after each.
- `render TEXT...`: the text rendered read-only as the result line renders it: the widget tree, and the renderer's swallowed exceptions as `log` rows.
- `paint TEXT...`: the painter's boxes for a history item in math mode, depth first: `x y w h above below`.
- `shot TEXT... --png FILE`: the whole window with the text typed in, at `--size WxH` and `--theme NAME`.
- `grade FILE [FILE]`: grades a table against python-flint; with two tables, the ulp histogram of each and how many rows got better or worse.

The window commands run offscreen on settings and history of a temporary folder; the app's own settings and history are not read or written.

```
$ scripts/probe layers "\root{8}{3}" --ref
input          layer    type      value                                               unit  expected  error
\root{8}{3}    tokens   str       Latex:\root{8}{3}:Root
\root{8}{3}    flat     str       8 ⌄ 3
\root{8}{3}    rpn      str       \root{8}{3}
\root{8}{3}    nodes    str       [(2, <LatexKind.Root: 2>, [(0, '8')], [(0, '3')])]
\root{8}{3}    split    str       Root  left 8  right 3
\root{8}{3}    binding  Rational  2/1                                                 DEG   2         exact
\root{8}{3}    written  str       2
⌄ int:8 int:3  apply    Rational  2/1                                                 DEG   2         exact
⌄ int:8 int:3  written  str       2

$ scripts/probe editor "\frac{1}{2}" --step left --step text:7
input        layer   type  value                        plain
\frac{1}{2}  editor  str   '' Fraction<'1' ; '2|'> ''   \frac{1}{2}
left         editor  str   '' Fraction<'1' ; '|2'> ''   \frac{1}{2}
text:7       editor  str   '' Fraction<'1' ; '7|2'> ''  \frac{1}{72}
```

### Definitions

A value used in many inputs is defined once and named as `@NAME`; it is substituted in parentheses, so it binds as one operand (`editor` and `render` take it as typed).

```
$ scripts/probe eval "@M + 1" --def "M=2^{62}"
input                layer       type     value                      unit
(2^{62}) + 1         editor      str      (2^{62}) + 1
(2^{62}) + 1         eval        BigReal  4611686018427387905        DEG
```

`--defs FILE` reads `NAME=EXPR` lines; `#` starts a comment.

### Cases from a test suite

`--test NODEID` takes the inputs from a parametrized test's rows instead of copying them by hand; `-k` selects rows as pytest does. Without `--field` the rows and their params are listed; with it, the named param (or its attribute, `case.expr`) is the input, and the row's other params print beside it as `test.` columns.

```
$ scripts/probe eval --test tests/py/e2e/test_eval_e2e.py -k "root-domain-complex" --field expr
input     layer       type     value     unit  test.expected_type  test.expected_value
(-4) ⌄ 2  editor      str      (-4) ⌄ 2
(-4) ⌄ 2  eval        complex  2j        DEG   complex             (0.0, 2.0)
```

## scripts/native_probe

It builds itself on first use (`make native-probe`, after `make native-build` has configured the build tree).

- `literal TEXT...`: what a number literal denotes (`literal_value`).
- `apply OP OPERAND...`: one op on typed operands through `eval::apply`, as the evaluator calls it.
- `eval EXPR...`: `tokenize` and `evaluate`; `--no-closed-forms` sums and multiplies term by term.
- `tokens EXPR...`: the tokens after `tokenize`, `normalize` and `shunting_yard`.
- `promote OP OPERAND...`: the operands after each of apply's promotion steps.
- `kernel OP OPERAND... [--arms]`: the kernel alone, on operands of one arm the op has; `--arms` lifts them to each arm with `value.hpp`'s own lifts.
- `boost NAME TYPE ARG...`: a row of `kBoostRows` on `double`, `ldbl`, `dec50` or `bin`.

`--time N` adds the median nanoseconds of N runs as an `ns` column. A case it cannot read prints a `probe` row, and the cases after it still run.

### Typed operands

An operand is `KIND:VALUE`, in the form `probe layers` prints, so an input row pastes back as arguments: `int:-5`, `dbl:0.1` or `dbl:0x1.999999999999ap-4` (hexadecimal is the double exactly), `rat:1/3`, `big:0.1`, `cx:RE,IM`, `bigcx:RE+IMi`. A collection is printed as `list:[...]` but not read back. `--def NAME=KIND:VALUE` names one, used as `@NAME`.

```
$ scripts/native_probe apply root dbl:1e300 int:3 | scripts/probe grade -
input                               layer  type   value   unit  expected  error
⌄ dbl:0x1.7e43c8800759cp+996 int:3  apply  float  1e+100  DEG   1e+100    0 ulp

$ scripts/native_probe promote sqrt dbl:-4
input                        layer            type     value
√ dbl:-0x1.0000000000000p+2  in               float    -4.0
√ dbl:-0x1.0000000000000p+2  promote_big      float    -4.0
√ dbl:-0x1.0000000000000p+2  coerce           float    -4.0
√ dbl:-0x1.0000000000000p+2  promote_complex  complex  (-4+0j)
√ dbl:-0x1.0000000000000p+2  coerce           complex  (-4+0j)

$ scripts/native_probe tokens "2sin 30"
input    layer          type  value
2sin 30  tokenize       str   2  sin  30
2sin 30  normalize      str   2  ·  sin  30
2sin 30  shunting_yard  str   2  30  sin  ·
```

What `tokens` and `promote` do not show (the assignment peel, the real-first rewrite of a root) is in [probe-tools.md](superpowers/findings/probe-tools.md).

## native_tests --case

`src/native/build/native/native_tests --case ID -v` runs only the cases whose id starts with ID. The id is the path a failure line prints, its suite first; an id that matches no case fails with a message. The other suites still print their banners, with `0 PASSED`.

```
$ src/native/build/native/native_tests --case "unit test helpers :: print :: integer" -v
...
PASSED unit test helpers :: print :: integer EXPECT_EQ: printed(42) == "42"
...
```

## Where each command lives and what it calls

The Python commands are modules of `scripts/probes/`, run by `scripts/probe` (`python -m probes` with `src` and `scripts` on the path). The native commands are functions of `src/native/tools/probe/main.cpp`, built as the CMake target `native_probe` and run by `scripts/native_probe`.

Python, by command:

- `eval`: `eval_cmd.py`. `Expression.set_plain_text` and `get_plain_text` (the editor's text), `tcalc.core.parser.tokenize`, `tcalc.core.native_eval.evaluate_branch`, `tcalc.ui.controller.utils.format_result`.
- `layers`: `layers.py`. `calc_native.tokenize_string`, `tokens_to_flat_text`, `shunting_yard`, `build_math_nodes`, `structural_split`, `evaluate`, `root_operands` and `apply` (the last op alone), `format_result`.
- `editor`: `editor.py`. A real `MainWindow` (`app.py`'s `app_window`), keys through `QTest` into the app's keyboard handler, `key:NAME` through `controller.handle_key` with the `Operation`, the tree from `tcalc.debug.snapshot_slot` (`tree.py`).
- `render`: `render.py`. An `ExpressionSlot` and `MathRender(read_only=True).render_node`, as the result line renders; the swallowed exceptions read from the `tcalc.ui` logger.
- `paint`: `paint.py`. `MathPainter.paint_tree` with a history item's font, placed by `PaintCanvas.set_tree`.
- `shot`: `shot.py`. `MainWindow`, `set_plain_text`, the result label's text, `QWidget.grab`.
- `grade`: `grade.py` and `grade_cmd.py`. python-flint (`acb`, `arb`) at 80 digits, one meaning per `OpId` in its table; a BigReal residual through `calc_native.apply(Sub)`.

The shared frame: `rows.py` (the row, the value and operand texts, the table), `options.py` (the flags of every command), `defs.py` (`@NAME`), `testcase.py` (`--test`, `--field`, through pytest's own collection), `app.py` (the offscreen app isolated on a temporary folder, the styled app, the window, `--png`).

Native, by command (`main.cpp` unless named):

- `literal`: `eval::literal_value` (`lib/eval/pub/literal.hpp`).
- `apply`: `eval::apply` (`lib/eval/pub/eval.hpp`).
- `eval`: `parser::tokenize`, `eval::evaluate`, `eval::set_closed_forms_enabled`.
- `tokens`: `parser::tokenize`, `eval::normalize`, `eval::shunting_yard`, `parser::token_text`.
- `promote`: `eval::promote_big`, `eval::coerce`, `eval::promote_complex`, in apply's order.
- `kernel`: `ops::kernel_of`, `ops::arms_of` (`lib/parser/pub/ops.hpp`); `--arms` lifts with `to_double`, `to_complex`, `to_big`, `to_big_complex`, `to_rational` (`lib/value.hpp`).
- `boost`: `boost_table.cpp`, Boost.Multiprecision called directly.

The shared frame is `frame.hpp`: typed operands (`parse_operand`), the value texts in the Python forms (`exact_text`, `value_text`, `operand_text`), the table (`print_rows`), `@NAME` (`substitute`) and the timing (`median_ns`).

## When no command answers the question

A question no command answers gets its command or option written into the frame and kept, not a throwaway script beside it:

- Python: a module in `scripts/probes/` with a `run(options)` that prints rows through `rows.format_rows`, a `Command` row in `__main__.py` with its help and example, a `Layer` member in `rows.py` for each new layer, a flag in `options.py` only if no existing one fits.
- Native: a `run_*` function in `main.cpp` that returns rows, a `Command` row in `kCommands`, a `Flag` only if no existing one fits; a Boost function is a row of `kBoostRows`. A new layer name gets its `Layer` member in `rows.py`, so `probe grade` reads the table.
- Its line in this file: the command, where it lives, what it calls, one example run with its real output.

A throwaway script is only for what the frame cannot reach, and the finding that used it says why.

## For an AI agent

- Read this file before writing any script to look at a case; the command probably exists.
- Run the narrowest command first (`eval`, then `layers`), and paste the table with its command into the report: it is the evidence `docs/rules/ai/psychosis.md` asks for.
- Copy an input from a row, not by hand: a typed operand row pastes back into `native_probe` exactly, a double as its hexadecimal form; `list:` does not.
- Give the unit (`--unit`) whenever an angle is involved; every value row carries it.
- A test row is read with `--test` and `--field`, not retyped.
- The window commands never touch the user's settings or history; no command needs the real app running.
- A missing command is written into the frame and documented here, as the section above says, in the same change.
