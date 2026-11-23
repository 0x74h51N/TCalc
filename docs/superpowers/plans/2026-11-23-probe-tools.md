# Probe Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two commands, `scripts/probe` (Python) and `scripts/native_probe` (C++), that show one case on one layer of TCalc at a time, grade it against python-flint, and run any case a test suite holds by its id.

**Architecture:** A Python package `scripts/probes/` holds the shared pieces (value rows, definitions, the grader, test row collection, the slot tree dump) and one module per command, dispatched from one command table. A C++ executable in `src/native/tools/probe/` links `calc_core`, reads typed operands through one frame header, and runs one function per command from its own table. Both print the same aligned value rows, which `probe grade` reads.

**Tech Stack:** Python 3.14, PySide6, pytest, python-flint (new dev dependency, typed), C++20 with Boost.Multiprecision and Boost.Math, CMake and Ninja.

**Spec:** `docs/superpowers/specs/2026-11-23-probe-tools-design.md`

**Decided while executing (2026-11-23):** the package is imported as `probes` (`PYTHONPATH=src:scripts`), the name mypy maps `scripts/probes` to; where a task below writes `scripts.probes.X`, read `probes.X`. The tools get no unit tests (human agent, 2026-11-23): a test script is tested end to end, in `tests/py/e2e/test_probes_e2e.py` through `main` on the real binding, rows as frozen dataclasses with placeholder values, never a case from a bug. Where a task below names a unit test or `tests/py/unit/probes`, it is an e2e row in that file instead; the native probe is tested by running it. The value types are looked up in one table in `rows.py`.

**Changed while executing (2026-11-23), the rulings in full in the ledger:** there is no `probe widget` (`render` reaches each widget) and no `latex:KIND` step; `probe editor` runs the app's own `MainWindow` and takes its steps by `--step`, the tree from `tcalc.debug.snapshot_slot` instead of a new `slot_tree`; `isolate_app` lives in `probes/app.py`, beside `styled_app` and `app_window`; `probe shot` is the window only, by `--png`, `--size` and `--theme`, a fresh window per text; the native value texts follow Python's (`repr`, `decimal_text(value, 0)`) and a double operand is written in `float.hex`'s form; `bigcx:` is `decimal_text`'s form and `list:` is not read natively; `scripts/native_probe` always runs its ninja target and the probe target has no configure step (it deletes the built module); `native_probe` gets no `subprocess` e2e tests (human agent); `native_tests --case` takes the id with its suite first, has no on-the-way rule, and fails when nothing matches; `kBoostRows` starts empty and the Boost argument reader goes through `frame.hpp`'s readers.

## Global Constraints

- No em dash anywhere: code, comments, Markdown, commit messages.
- Everything written into the repository is in English.
- Python: annotated under mypy `strict`; `X | None`, built-in generics; a value that can be anything is `object`; narrowing by `isinstance`, never `cast`; every `# type: ignore` names its code.
- A native value never loses precision on the Python side: no `float()`, `int()`, `to_double()` of a `Rational`, `BigReal` or `BigComplex`. A `Collection` is read through its own API (`len`, `preview()`, `kind`).
- `==` on a bound type compares identity: two values are the same when their type name and exact text are equal.
- Native: builds with `TCALC_WARNINGS`; named casts only; no bare numeric literal, each is a named `constexpr`; a closed set is an `enum class` and a `switch` over it names every value with no `default`; no `NOLINT` in this code.
- Inputs are given at the moment of use: the tools hold no case, constant or shorthand, and the Boost table starts empty.
- Values in docs and output are in the flat op form (`(2)⌄(3)`, `(2)⁻¹`).
- No unit tests for the tools: they are tested end to end through `scripts/probe` and `native_probe` (see the note above).
- The tools are run with the `.venv` interpreter only.
- No commit without the human agent's approval: every commit step below is "show the diff, wait, then commit". Before it, `make py-lint-fix` and, when C++ changed, `make cpp-format`.

## Review Focus

- An `@NAME` used inside a longer word or next to a digit (`@M2`, `2@M`): the name ends at the first character that is not a letter, digit or underscore, and the substituted text is parenthesized, so `2@M` reads as `2(...)`. Pinned in Task 1.
- A test node id that collects nothing, or a parametrized row whose `--field` path does not exist: an error naming the id or the path, not an empty run. Pinned in Task 3.
- A double result whose correctly rounded expected value is `0` or subnormal: the ulp count uses `math.ulp` of the expected value, and an expected `0` with a nonzero result reports the result's magnitude, not a division by zero. Pinned in Task 2.
- A reference ball too wide to fix one double: the row says so, it does not show an ulp count. Pinned in Task 2.
- A typed native operand a type cannot hold whole (`int:9223372036854775808`, `rat:1/0`, `dbl:abc`): an error naming the operand, before any layer runs. Pinned in Task 8.

## File Structure

Python, new:
- `scripts/probe`: shell wrapper; `.venv` python, `PYTHONPATH=src:<root>`, `-m scripts.probes`.
- `scripts/probes/__init__.py`: empty, makes the package visible to mypy.
- `scripts/probes/__main__.py`: the command table and argument parsing shared by every command.
- `scripts/probes/rows.py`: the value row, its text, aligned output and reading it back.
- `scripts/probes/defs.py`: `--def`, `--defs` and `@NAME` substitution.
- `scripts/probes/grade.py`: the python-flint references, the op meaning table, ulps, the BigReal residual, the two run comparison.
- `scripts/probes/testcase.py`: `--test` and `--field`.
- `scripts/probes/app.py`: the offscreen `QApplication`, isolated and styled as `run_app` styles it.
- `scripts/probes/tree.py`: the slot tree dump.
- One module per command: `eval_cmd.py`, `layers.py`, `grade_cmd.py`, `editor.py`, `render.py`, `widget.py`, `paint.py`, `shot.py`.

Native, new:
- `src/native/tools/probe/frame.hpp`: typed operands, value text, the row printer, timing.
- `src/native/tools/probe/main.cpp`: the command table and the commands.
- `src/native/tools/probe/boost_table.cpp`: the Boost rows, empty.
- `scripts/native_probe`: shell wrapper; builds when stale, then runs.

Modified: `pyproject.toml`, `makefile`, `src/native/CMakeLists.txt`, `src/native/Makefile`, `scripts/changed_jobs`, `tests/py/helpers.py`, `tests/py/e2e/ui/test_view_state_ui_sync.py`, `tests/py/e2e/ui/test_theme_switch.py`, `src/native/tests/main.cpp`, `src/native/tests/internal/test_helpers.hpp`, `src/native/tests/test_test_helpers.cpp`, `CLAUDE.md`, `docs/dev.md`, `docs/CONTRIBUTING.md`, `docs/rules/ai/tests.md`, `docs/rules/ai/efficiency.md`.

New test files: `tests/py/e2e/test_probes_e2e.py`, `tests/py/e2e/ui/test_probes_ui.py`.

The scratch probes each task replaces are named in the task: they live in old session scratchpads, so the logic the task takes from them is written into the task.

### Task 1: Package, wrapper, value rows and definitions

Replaces the per script setup every scratch probe repeated (`PYTHONPATH=.:src:tests/py/e2e`, a print loop per case).

**Files:**
- Create: `scripts/probe`, `scripts/probes/__init__.py`, `scripts/probes/__main__.py`, `scripts/probes/rows.py`, `scripts/probes/defs.py`
- Modify: `pyproject.toml` (`[tool.mypy] files` adds `"scripts/probes"`), `scripts/changed_jobs` (`PYTHON` adds `"scripts/probes/*"`)

**Interfaces:**
- Produces:
  - `class ProbeError(Exception)` in `rows.py`: every user facing failure of the tools; `__main__` prints its message and exits 2.
  - `@dataclass(frozen=True) class Row: input: str; layer: str; type: str; value: str; extra: tuple[tuple[str, str], ...] = ()` (extra columns such as `expected`, `ulps`, by header name).
  - `type_name(value: object) -> str`: `type(value).__name__` (`int`, `float`, `complex`, `Rational`, `BigReal`, `BigComplex`, `Collection`).
  - `value_text(value: object) -> str`: `float` and `complex` by `repr`; `Rational` as `f"{n}/{d}"`; `BigReal`, `BigComplex` by `calc_native.decimal_text(value, 0)`; `int` by `str`; `Collection` by `preview()`.
  - `exact_text(value: object) -> str`: as `value_text`, except a `float` is `value.hex()`, a `complex` is `f"{re.hex()},{im.hex()}"`.
  - `operand_input(op_symbol: str, operands: Sequence[object]) -> str`: the typed operand input, `"⌄ dbl:0x1.0000000000000p+1 int:3"`. Each operand is written in `native_probe`'s own operand form (`int:`, `dbl:`, `rat:P/Q`, `big:`, `cx:RE,IM`, `bigcx:RE,IM`) with its exact text, so a row's input pasted after `scripts/native_probe apply` runs the same operands natively. The `type` column keeps the Python names; only the input uses the operand prefixes.
  - `format_rows(rows: Sequence[Row]) -> str`: a header line from the fields and the extra column names, every column padded to its widest cell, two spaces between columns.
  - `parse_rows(text: str) -> list[Row]`: reads what `format_rows` wrote, by the header's column starts.
  - `parse_defs(lines: Iterable[str]) -> dict[str, str]`: `NAME=EXPR` per line, blank lines and lines starting with `#` skipped; a line without `=` or a name that is not an identifier raises `ProbeError`.
  - `substitute(text: str, defs: Mapping[str, str]) -> str`: each `@NAME` (NAME `[A-Za-z_][A-Za-z0-9_]*`) becomes `(EXPR)`; an undefined name raises `ProbeError(f"undefined @{name}")`.
  - `__main__.py`: `@dataclass(frozen=True) class Command: name: str; run: Callable[[argparse.Namespace], int]; help: str; example: str` and `COMMANDS: tuple[Command, ...]`; shared options on every command: `inputs` (positional, `-` reads stdin lines), `--def` (repeatable), `--defs FILE`, `--ref`. `main(argv: Sequence[str] | None = None) -> int`. With no command it prints each command's name, help and example.

- [ ] **Step 1: Write the failing tests**

`tests/py/e2e/test_probes_e2e.py`, through `main`, one parametrized table:

```python
# text, defs, expected
param("(0.5)⌄@M", {"M": "-9223372036854775807-1"}, "(0.5)⌄(-9223372036854775807-1)", id="one name"),
param("2@M", {"M": "3"}, "2(3)", id="after a digit"),
param("@M2+@M", {"M": "1", "M2": "2"}, "(2)+(1)", id="longest name"),
param("M+1", {"M": "3"}, "M+1", id="bare name is a variable"),
```

and `substitute("@X", {})` raises `ProbeError` whose text contains `@X`. `parse_defs(["M=1", "", "# c", "N = 2"])` is `{"M": "1", "N": "2"}`; `parse_defs(["oops"])` raises `ProbeError`.

The same file: `parse_rows(format_rows(rows)) == rows` for two rows with an extra column; `format_rows` of two rows of different widths has its `type` column starting at the same offset on every line. `value_text` and `exact_text`: one row per arm on real values. `exact_text(0.1) == (0.1).hex()`.

- [ ] **Step 2: Run them to see them fail**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q`
Expected: FAIL at import, `ModuleNotFoundError: scripts.probes`.

- [ ] **Step 3: Implement `rows.py`, `defs.py`, `__main__.py` and `scripts/probe`**

`scripts/probe` is three lines after the shebang: `root=$(cd "$(dirname "$0")/.." && pwd)`, then `PYTHONPATH="$root/src:$root" exec "$root/.venv/bin/python" -m scripts.probes "$@"`. `COMMANDS` is empty in this task; later tasks add a row each. The command list ends with one line naming the ASCII aliases the tokenizer reads, taken from the ops table at run time (`tcalc.core.ops`), so `⌄` and `⁻¹` need not be typed.

- [ ] **Step 4: Run the tests and the checks**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q && make typecheck && make py-lint`
Expected: all pass. `scripts/probe` prints an empty command list and exits 0.

- [ ] **Step 5: Show the diff and wait for approval, then commit**

```bash
git add scripts/probe scripts/probes pyproject.toml scripts/changed_jobs tests/py/e2e/test_probes_e2e.py
git commit -m "chore/probe: value rows, definitions and the probe command"
```

### Task 2: Grader and `probe grade`

Replaces `cr.py` (correctly rounded double, ulps per complex part), `arms.py`'s `bigdiff` (BigReal minus exact through `apply(Sub)`) and `p231/grade.py` (ulp histogram, old against new).

**Files:**
- Create: `scripts/probes/grade.py`, `scripts/probes/grade_cmd.py`
- Modify: `pyproject.toml` (`dev` adds `"python-flint>=0.9,<0.10"`), `scripts/probes/__main__.py` (row `grade`), `tests/py/e2e/test_probes_e2e.py`

**Interfaces:**
- Consumes: `Row`, `Layer`, `parse_rows`, `format_rows`, `ProbeError`, `OperandKind`, `type_name` (Task 1).
- Produces:
  - `REF_DIGITS = 80`, set with `flint.ctx.workdps` around each reference.
  - One reference type, `flint.acb`; a real value is an `acb` whose imaginary part is an exact zero.
  - `OP_MEANINGS: dict[calc_native.OpId, Callable[[Sequence[acb]], acb]]`: one row per op, TCalc's meaning. `Root` and `Pow` at a rational exponent `p/q` with `q` odd on a negative real are the real root (`-(|x|.root(q))` to the power), else the principal value; everything else is python-flint's principal value. The rows are written from `docs/glossary.md` and each op's kernel; an op with no row grades as `not graded`.
  - `CONST_MEANINGS: dict[calc_native.ConstId, Callable[[], acb]]`: `Pi`, `EulerNumber`, `GoldenRatio`, `Tau`, `Imaginary` from python-flint; every other constant from the decimal text of its `const_table()` value.
  - `exact_of_decimal(text: str) -> acb`: a typed decimal (`"0.1"`, `"1e400"`) read exactly through `fractions.Fraction` and `fmpq`.
  - `expected_of_expression(text: str) -> acb | None`: walks `calc_native.shunting_yard(calc_native.tokenize_string(text).tokens)`: a number token by `as_number().value`, a constant by `CONST_MEANINGS`, a paren and a call token by recursion on their elements and args, a LaTeX token by its `op_id`, `left` and `right`; `None` when an op, a constant or a token kind (a variable) has no meaning.
  - `expected_of_operands(op: calc_native.OpId, operands: Sequence[str]) -> acb | None`: each operand in the operand form (`OperandKind`) read as held.
  - `double_of(value: acb) -> float | complex | None`: per part, the double both ends of the ball round to; `None` when a part's ends round to different doubles.
  - `ulps(got: float, want: float) -> int`: `0` when equal; when `want == 0`, `got`'s distance in ulps of the smallest subnormal; else `round(abs(got - want) / math.ulp(want))`.
  - `bigreal_residual(value: calc_native.BigReal, exact: acb) -> tuple[str, str]`: `apply(calc, OpId.Sub, [value, BigReal(exact.real.str(REF_DIGITS, radius=False))], RAD)` as `decimal_text(_, 0)`, and the residual relative to `exact`.
  - `grade(row: Row) -> Row`: the reference by the input column (a first word that is one op and every other word an operand means operands; otherwise an expression); adds the columns `expected` and `error` (`N ulp`, `N ulp, N ulp` for the parts of a complex, `residual R rel E` for a BigReal, `no single double`, `not graded`).
  - `compare(a: Sequence[Row], b: Sequence[Row]) -> str`: rows lined up by `input` and `layer`, a row with no partner listed; an ulp histogram per side (buckets `0` to `8`, then `9+`), and the counts better and worse.
  - `grade_cmd.run(options: Options) -> int`: `probe grade FILE [FILE]` (`-` is stdin), one file graded, two compared.

- [ ] **Step 1: Write the failing e2e tests** in `tests/py/e2e/test_probes_e2e.py`, rows as frozen dataclasses with placeholder values: `ulps` (equal is `0`, the next double up is `1`, an expected `0` with the smallest subnormal is `1`); `double_of` (a ball of an exact `1/2` gives `0.5`, a ball of radius `1e-10` around `1` gives `None`); `compare` of two one row lists with ulps `2` and `0` reports `better 1 worse 0`; `grade` picks the operand reference for an operand input and the expression reference for an expression, each through `probe grade` on a table.

- [ ] **Step 2: Run them to see them fail.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q`. Expected: FAIL, `ModuleNotFoundError` on `probes.grade`.

- [ ] **Step 3: Implement `grade.py` and `grade_cmd.py`**, add python-flint to the dev extra and run `make install`.

- [ ] **Step 4: Write the e2e tests** in `tests/py/e2e/test_probes_e2e.py`: one row per `OP_MEANINGS` entry against python-flint directly; `expected_of_expression` on the real tokenizer, one row per token kind it descends into (a paren op, a call, a LaTeX fraction, a constant), and a variable gives `None`; `bigreal_residual` of the real `BigReal` of `1/3` against the exact `1/3` is `0`.

- [ ] **Step 5: Run the e2e tests.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q && make typecheck`. Expected: all pass.

- [ ] **Step 6: Show the diff and wait for approval, then commit** `chore/probe: grade a value row against python-flint`.

### Task 3: Cases from the Python test suites (`--test`, `--field`)

Replaces copying a row out of `test_eval_e2e.py` by hand (`from test_eval_e2e import _eval`, 16 scratch probes).

**Files:**
- Create: `scripts/probes/testcase.py`
- Modify: `scripts/probes/__main__.py` (shared options `--test`, `-k`, `--field`), `tests/py/e2e/test_probes_e2e.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class TestRow: nodeid: str; params: Mapping[str, object]`.
  - `collect(target: str, keyword: str | None) -> list[TestRow]`: `pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", target, *(["-k", keyword] if keyword else [])], plugins=[collector])`, the collector keeping `session.items` in `pytest_collection_finish`. pytest's own output goes to a buffer (`contextlib.redirect_stdout`) so it does not mix with the rows; it is printed only when collection fails. An item with no `callspec` is skipped; no row collected raises `ProbeError(f"no parametrized case for {target}")` with the buffered output.
  - `field(row: TestRow, path: str) -> object`: the first segment is a param name, the rest are attributes (`case.expr`); a missing segment raises `ProbeError` naming the path and the row's param names.
  - `__main__` resolves inputs: with `--test` and `--field`, each row's field is an input and the row's other params print as extra columns of that input's rows; with `--test` and no `--field`, the rows' params are printed and no command runs.

- [ ] **Step 1: Failing e2e tests** for `field`, on real rows of `test_eval_e2e.py`: `field(TestRow("t", {"case": Case(expr="1")}), "case.expr") == "1"`; `field(TestRow("t", {"expr": "1"}), "expr") == "1"`; a missing path raises `ProbeError` whose text names `case.nope` and `case`.

- [ ] **Step 2: Run, see them fail.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q`. Expected: FAIL, import error.

- [ ] **Step 3: Implement `testcase.py` and the `__main__` options.**

- [ ] **Step 4: e2e test** in `test_probes_e2e.py`: `collect("tests/py/e2e/test_eval_e2e.py::test_native_eval_golden[precedence-mul-over-add]", None)` gives one row whose `expr` is `"1+2*3"` and `expected_value` `7.0`; `collect("tests/py/e2e/test_eval_e2e.py", "root-cube")` gives rows whose `case` is a `RootCase`; `collect("tests/py/e2e/test_eval_e2e.py::nope", None)` raises `ProbeError`.

- [ ] **Step 5: Run.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q && make typecheck`. Expected: pass.

- [ ] **Step 6: Show the diff, wait for approval, commit** `chore/probe: run a case from a test suite by its id`.

### Task 4: `probe eval` and `probe layers`

Replaces `types.py` (editor text, `evaluate_branch`, type and value per row) and the `tokenize`, `shunting_yard`, `apply` probes; `probe layers`' op alone row is `arms.py`'s `n.apply(c, op, args, U)`.

**Files:**
- Create: `scripts/probes/app.py`, `scripts/probes/eval_cmd.py`, `scripts/probes/layers.py`
- Modify: `scripts/probes/__main__.py` (rows `eval`, `layers`), `tests/py/e2e/test_probes_e2e.py`

**Interfaces:**
- Consumes: `Row`, `value_text`, `exact_text`, `type_name`, `operand_input`, `format_rows` (Task 1); `grade` (Task 2).
- Produces:
  - `app.py`: `offscreen_app() -> QApplication`: sets `QT_QPA_PLATFORM=offscreen` and `QT_LOGGING_RULES=*=false` when unset, returns `QApplication.instance()` or a new one named `TCalc`.
  - `eval_rows(text: str) -> list[Row]`: through `tests.py.helpers.editor_canonical`, `tcalc.core.parser.tokenize`, `tcalc.core.native_eval.evaluate_branch` (fresh `Calculator`, `AngleUnit.RAD`, `calc_native.clear_vars()` first); layers `editor` (the canonical text as value, type `str`), `eval`, `display` (`format_result(v, group=True)`), `written` (`format_result(v)`), `round trip` (`same` or the second value's type and exact text). A raised error is a row whose type is the error class name and whose value is its message.
  - `layer_rows(text: str) -> list[Row]`: `tokens` (each token as `kind:text` and, for an op, call or LaTeX token, its `OpId` name), `flat` (`tokens_to_flat_text`), `rpn` (`shunting_yard` as token texts), `nodes` (`build_math_nodes` and `structural_split`, only when a token is LaTeX), `binding` (`calc_native.evaluate`, no editor), `op alone` (the last RPN token: an op's operands are the RPN tokens before it each evaluated alone through `calc_native.evaluate(calc_native.classify_tokens([t]), ...)`, a call's are its `args`, a LaTeX token's its `left` and `right`; the row's input is `operand_input`), `format` (`format_result` of the binding value).

- [ ] **Step 1: Write the e2e tests** (they cross the real binding, so e2e): `eval_rows("1/3")` has an `eval` row of type `Rational` and value `1/3`, and a `round trip` row `same`; `eval_rows("1/0")` has an `eval` row whose type is an error class; `layer_rows("(2)⁻¹")` has an `op alone` row with input `⁻¹ int:2` and value `1/2`; `layer_rows("\\root{3}{8}")` has an `op alone` row read from the LaTeX token, with value `2` (exact arm); `layer_rows("sqrt(2)")` reads its operand from the call's args.

- [ ] **Step 2: Run, see them fail.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q`. Expected: FAIL, import error.

- [ ] **Step 3: Implement `app.py`, `eval_cmd.py`, `layers.py` and the two command rows.** `--ref` passes each row with a value through `grade`.

- [ ] **Step 4: Run, then use it.** Run the tests, `make typecheck`, then `scripts/probe layers "(2) root (3)" --ref` and `scripts/probe eval --test "tests/py/e2e/test_eval_e2e.py" -k root-cube --field case.expr --ref`. Expected: tests pass; the two commands print aligned rows with an `expected` and an `error` column; paste both outputs into the report.

- [ ] **Step 5: Show the diff, wait for approval, commit** `chore/probe: eval and layers commands`.

### Task 5: One isolation for the UI fixtures and the probes

Replaces the `QSettings` factory and `load_history` patches written in 49 scratch probes and in two fixtures.

**Files:**
- Modify: `tests/py/helpers.py`, `tests/py/e2e/ui/test_view_state_ui_sync.py:45-75`, `tests/py/e2e/ui/test_theme_switch.py:49-70`, `scripts/probes/app.py`

**Interfaces:**
- Produces: `isolate_app(folder: Path) -> None` in `scripts/probes/app.py`: `QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(folder / "config"))`, `os.environ["XDG_DATA_HOME"] = str(folder / "data")`, `tcalc.app_state._app_state = None`. `offscreen_app(isolated_in: Path | None = None, theme: str | None = None) -> QApplication` (Task 4's function extended): when `isolated_in` is given, `isolate_app` runs first; then it styles the app as `tcalc.ui.app.run_app` does (`init_styles` with the theme the app state holds, or `theme` when named).

- [ ] **Step 1: Switch the two fixtures.** Each replaces its `factory` and its `monkeypatch.setattr` lines for `QSettings`, `load_history` and `save_history` with `isolate_app(tmp_path)`. It keeps two `monkeypatch` lines, so teardown puts back what the helper changed in the process: `monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))` and `monkeypatch.setattr(app_state_mod, "_app_state", None)`, both before the helper. `test_theme_switch.py`'s `state` fixture yields its `factory`, and `window` calls `state()` to write saved pads: it now yields `lambda: QSettings("TCalc", "TCalc")`, which the helper has redirected. This is a relocation: no new test.

- [ ] **Step 2: Run the two files.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/ui/test_view_state_ui_sync.py -q` and the same for `test_theme_switch.py`, each in its own process. Expected: the same pass counts as before the change (record both before Step 1).

- [ ] **Step 3: Extend `offscreen_app`.**

- [ ] **Step 4: Show the diff, wait for approval, commit** `test/ui: one isolation helper for a window under test`.

### Task 6: Slot tree, `probe editor`, `probe render`, `probe widget`

Replaces `probe184c_dump.py`'s `dump(slot, mark)` and the `probe184*.py`, `probe_left.py`, `probe_cells.py`, `probe_enter.py` loops; the dump reads the tree through Qt, not `_segments`.

**Files:**
- Create: `scripts/probes/tree.py`, `scripts/probes/editor.py`, `scripts/probes/render.py`, `scripts/probes/widget.py`, `tests/py/e2e/ui/test_probes_ui.py`
- Modify: `scripts/probes/__main__.py` (rows `editor`, `render`, `widget`)

**Interfaces:**
- Produces:
  - `slot_tree(slot: ExpressionSlot, cursor: QLineEdit | None) -> str`: the slot's items in layout order (`slot.layout().itemAt(i).widget()`); a field as its quoted text with `|` at the cursor when it is `cursor`; a Math Widget as `Name<slot ; slot>`, the name its class name without `Widget`, its slots from `findChildren(ExpressionSlot, Qt.FindChildOption.FindDirectChildrenOnly)`; a paren glyph as its class name.
  - `editor_rows(text: str, steps: Sequence[str]) -> list[Row]`: an `Expression`, `set_plain_text`, events processed; a row `start` then one per step, value `slot_tree(editor root slot, QApplication.focusWidget())` and an extra column `plain` (`get_plain_text()`). Steps: `left`, `right`, `up`, `down`, `bs`, `key:NAME` (`op = Operation[NAME]`, a Python enum, `apply_key(op.symbol, op)`), `latex:KIND` (`insert_expr_str(calc_native.LatexKind.__members__[KIND])`, since a fraction or a root is no `Operation` member), `text:TEXT`; any other step raises `ProbeError` naming it.
  - `render_rows(text: str) -> list[Row]`: `logging.getLogger("tcalc.ui").setLevel(DEBUG)` with a handler that turns each record into a row of layer `log`; `MathRender(read_only=True).render_node(slot.default_input(), tokenize(text))` on a fresh `ExpressionSlot(InputKind.MAIN, "probe", InputAlign.<the result line's>)`, built as `result.py` builds its slot; a `tree` row.
  - `widget_rows(kind: str, left: str, right: str | None) -> list[Row]`: the class `MathRender.LATEX_KIND_MAP[calc_native.LatexKind.__members__[kind]]` (pybind enums are not subscriptable, measured 2026-11-23; the names are `Frac`, `Pow`, `Root`, `Subscript`); its fields in order from `line_edits()` get `left` and `right`; rows `tree` and `text` (`to_plain_text()`). An unknown KIND raises `ProbeError` listing the names.
  - `--png FILE` on these three: `QWidget.grab().save(FILE)` of the widget printed.

- [ ] **Step 1: Write the e2e test** in `tests/py/e2e/ui/test_probes_ui.py` (on the test themes, as the directory requires): `slot_tree` of an `Expression` set to `\frac{1}{2}+3` with the cursor at the end is `Frac<'1' ; '2'> '+3|'`; `editor_rows("\\frac{1}{2}", ["left", "bs"])` has three rows (`start`, `left`, `bs`), the cursor mark `|` appears exactly once in each row's tree, and the `left` row's cursor is one place left of the `start` row's.

- [ ] **Step 2: Run, see it fail.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/ui/test_probes_ui.py -q`. Expected: FAIL, import error.

- [ ] **Step 3: Implement the four modules and the rows.**

- [ ] **Step 4: Run and use.** Run the test and `make typecheck`, then `scripts/probe editor "\frac{1}{2}" left left bs --png /tmp/e.png` and `scripts/probe render "\root{3}{8}"`, and look at the picture. Expected: pass; the tree rows print; the PNG shows the editor.

- [ ] **Step 5: Show the diff, wait for approval, commit** `chore/probe: editor, render and widget commands`.

### Task 7: `probe paint` and `probe shot`

Replaces `shot.py` and `grab_win.py` (a `MainWindow` at a size and a theme, `grab().save`) and the painter probes.

**Files:**
- Create: `scripts/probes/paint.py`, `scripts/probes/shot.py`
- Modify: `scripts/probes/__main__.py` (rows `paint`, `shot`), `tests/py/e2e/ui/test_probes_ui.py`

**Interfaces:**
- Consumes: `offscreen_app` (Task 5), `slot_tree` (Task 6).
- Produces:
  - `paint_rows(text: str) -> list[Row]`: the font `HistoryItem._math_paint` builds (`QFont(app.font())`, point size `get_theme().look.history.math_font_size`); `MathPainter().paint_tree(tokenize(text), font)`; one row per box, depth first, value `x y w h above below` and, for a `TextLeaf`, its text; layer the box's class name, indented by depth. (`layout.Row` is imported under the name `BoxRow` beside the probes' `Row`.) `--png FILE` grabs a `PaintCanvas` holding the tree.
  - `shot(target: Literal["window", "editor", "paint", "widget"], out: Path, size: QSize | None, theme: str | None, text: str | None) -> list[Row]`: the window under `offscreen_app(isolated_in=<temp dir>, theme=theme)`, `--input` typed into its editor with `set_plain_text`; rows `editor` (plain text) and `result` (the result line's text) for a window.

- [ ] **Step 1: e2e test**: `paint_rows("\\frac{1}{2}")` has a row per box and its first row is a `Row` box at `x 0`; `shot("window", tmp_path / "w.png", QSize(800, 600), None, "1/3")` writes a PNG of that size and its `editor` row is `1/3`.

- [ ] **Step 2: Run, see it fail; Step 3: implement; Step 4: run and look at the PNG.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/ui/test_probes_ui.py -q && make typecheck`, then `scripts/probe shot window --input "1/3" --out /tmp/w.png`. Expected: pass, and the picture shows the window with `1/3` and its result.

- [ ] **Step 5: Show the diff, wait for approval, commit** `chore/probe: paint and shot commands`.

### Task 8: `native_probe` frame, target and wrapper

Replaces the C++ probe's `main`, its `scanf` row loop, `%.17g` output and `chrono` loop (`p231/final.cpp`, 46 files with `chrono`).

**Files:**
- Create: `src/native/tools/probe/frame.hpp`, `src/native/tools/probe/main.cpp`, `src/native/tools/probe/boost_table.cpp`, `scripts/native_probe`
- Modify: `src/native/CMakeLists.txt` (target `native_probe EXCLUDE_FROM_ALL`, include dirs `lib` and `tools/probe`), `src/native/Makefile` (`probe: configure` builds `--target native_probe`), `makefile` (`native-probe:` runs `$(NATIVE_MAKE) probe`)

**Interfaces:**
- Produces, in `frame.hpp`, namespace `tcalc::probe`:
  - `Value parse_operand(std::string_view text)`: `int:` (`std::from_chars` to `std::int64_t`), `dbl:` (`std::from_chars` to `double`; a text starting `0x` has the prefix dropped and is read with `std::chars_format::hex`, which does not accept the prefix itself), `rat:P/Q` (two int64, `Q != 0`), `big:` (`BigReal(std::string(text))`), `cx:RE,IM`, `bigcx:RE,IM`; anything not read whole throws `ProbeError` naming the operand.
  - `struct ProbeError : std::runtime_error`.
  - `std::string type_name(const Value &v)`: the Python names (`int`, `float`, `complex`, `Rational`, `BigReal`, `BigComplex`, `Collection`), one `std::visit` overload per arm.
  - `std::string exact_text(const Value &v)`: `std::to_chars(..., std::chars_format::hex)` for a double prefixed `0x`, `p/q`, `str(0)` for `BigReal` (the digits it holds).
  - `std::string value_text(const Value &v)`: shortest round trip `std::to_chars` for a double, otherwise `exact_text`.
  - `struct Row { std::string input, layer, type, value; }`, `void print_rows(std::ostream &, std::span<const Row>)`: the same aligned header format as `rows.py` (Task 1).
  - `std::map<std::string, std::string> parse_defs(...)` and `std::string substitute(std::string_view operand, const std::map<...> &)`: `@NAME` to the defined typed operand text, undefined throws.
  - `template <class Fn> double median_ns(Fn &&fn, int runs)`: `std::chrono::steady_clock` around each call, the result written to a `volatile` sink so it is not removed, the median of `runs`.
  - `main.cpp`: `struct Command { std::string_view name, help, example; int (*run)(std::span<const std::string>); }` and `constexpr std::array kCommands`; this task adds `literal`, `apply` and `eval`. `apply` and the later commands read the op with `ops::find_op(token)`. Shared options: `--def`, `--defs FILE`, `--time N`, `-` for stdin. No command lists the commands; `CMD --help` prints the command's help and example.
- `scripts/native_probe`: `make -C <root> native-probe >/dev/null` when `src/native/build/native/native_probe` is missing or older than `src/native/build/native/libcalc_core.a`, then `exec` it with the arguments.

- [ ] **Step 1: Write the e2e checks** in `tests/py/e2e/test_probes_e2e.py`, running `scripts/native_probe` through `subprocess`: `literal` of `int:-9223372036854775808`, `rat:2/6` (`1/3`), `dbl:0x1.8p+1`, `big:0.1` prints the exact text; `int:9223372036854775808`, `rat:1/0`, `dbl:abc`, `nope:1` exit non zero with the operand named; `--def M=int:3` and `@M` reads `int:3`, an undefined name exits non zero.

- [ ] **Step 2: Run, see them fail.** Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_probes_e2e.py -q`. Expected: FAIL, no `scripts/native_probe`.

- [ ] **Step 3: Implement the frame, the three commands, the target, the Makefile rules and the wrapper.** `literal` prints `literal_value`; `apply` runs `eval::apply` on the parsed operands, the row input built from the op token and each operand in the operand form with its `exact_text` (`dbl:0x1.0p+1`), the same form `operand_input` writes (Task 1), so an input can be pasted back as arguments; `eval` runs `parser::tokenize` and `eval::evaluate`, `--no-closed-forms` calling `set_closed_forms_enabled(false)` first.

- [ ] **Step 4: Run and use.** Run: the e2e tests, then `scripts/native_probe apply root dbl:1e300 int:3 --time 1000 | scripts/probe grade -`. Expected: tests pass; the grade prints the row with an `expected` and an `error` column, and the timing column. Paste the output into the report.

- [ ] **Step 5: `make cpp-format`, show the diff, wait for approval, commit** `chore/native-probe: frame, literal, apply and eval`.

### Task 9: `native_probe` layer commands

Replaces the scratch probes that included `eval.hpp` and `calculator.hpp` to call `coerce`, a kernel or a Boost function directly (40 with the kernels, 21 with `roots.hpp`, `arms.py` for the arm comparison).

**Files:**
- Modify: `src/native/tools/probe/main.cpp`, `src/native/tools/probe/boost_table.cpp`

**Interfaces:**
- Consumes: the frame (Task 8).
- Produces, as rows of `kCommands`:
  - `tokens EXPR`: rows `tokenize`, `normalize`, `shunting_yard`, each the token texts (`parser::token_text`) joined by spaces.
  - `promote OP ARG...`: rows `in`, `promote_big`, `coerce`, `promote_complex` and, when that changed an arm, `coerce`; each row's value is the operands' types and `value_text`.
  - `kernel OP ARG... [--arms]`: `ops::kernel_of(id)(id, calc, args, unit)`; before it, operands of different types or a type outside `ops::arms_of(id)` throw `ProbeError` naming the types; `--arms` lifts the operands to each arm in `arms_of(id)` with `to_double`, `to_big`, `to_complex` and prints one row per arm; an arm `value.hpp` has no lift to from the given type (a `double` to `Rational`) gets a row saying so instead of a value.
  - `boost NAME TYPE ARG...`: `struct BoostRow { std::string_view name; ... }` with one generic lambda per row, called with the operands converted to `double`, `long double`, `cpp_dec_float_50` (`dec50`) or `cpp_bin_float_100` (`bin`); `kBoostRows` holds no row; an unknown NAME lists the rows (none) and says to add one in `boost_table.cpp`.

- [ ] **Step 1: Run it and see it fail**: the arm check, `kernel` on an `int` and a `float` operand of `Add` throws `ProbeError` whose text names both types; a `Root` on a type outside its arms throws.

- [ ] **Step 2: Run, see it fail; Step 3: implement; Step 4: run and use.** Run: the e2e tests, then `scripts/native_probe kernel root dbl:1e300 dbl:3 --arms` and `scripts/native_probe promote root rat:-8/1 rat:1/3`. Expected: tests pass; one row per arm; the promote rows show each step's types.

- [ ] **Step 5: `make cpp-format`, show the diff, wait for approval, commit** `chore/native-probe: tokens, promote, kernel and boost`.

### Task 10: `native_tests --case`

**Files:**
- Modify: `src/native/tests/internal/test_helpers.hpp` (`TestContext` gets `std::string case_filter{}`; `with_case` returns before running `fn` when the filter is set and neither `id.starts_with(filter)` nor `filter.starts_with(id + " :: ")` holds, `id` being `ctx.current_case` after the scope), `src/native/tests/main.cpp` (`--case ID` in the existing argument loop), `src/native/tests/test_test_helpers.cpp`

- [ ] **Step 1: Failing test**, a table of `(filter, id, runs)` through a local `TestContext`: `("exp :: ln two", "exp", true)`, `("exp :: ln two", "exp :: ln two", true)`, `("exp :: ln two", "exp :: ln ten", false)`, `("", "anything", true)`.

- [ ] **Step 2: Run, see it fail; Step 3: implement; Step 4: run** `make native-test` and `src/native/build/native/native_tests --case "print :: integer" -v`. Expected: pass; the second runs one case.

- [ ] **Step 5: `make cpp-format`, show the diff, wait for approval, commit** `test/native: run one case by its id`.

### Task 11: Docs

**Files:**
- Create: `docs/probe.md`
- Modify: `CLAUDE.md` (Commands: `scripts/probe` and `scripts/native_probe`, one line each), `docs/dev.md` (the same two and a link to `docs/probe.md`), `docs/CONTRIBUTING.md` (one line linking `docs/probe.md`), `docs/rules/ai/tests.md` (under Operation results: the layers are first looked at with the probe tools), `docs/rules/ai/efficiency.md` (under While working: a probe the skeleton lacks is added to it and kept; a throwaway script only for what it cannot reach, and the finding says why)

- [ ] **Step 1: Write `docs/probe.md`**: which question goes to which command (a wrong value: `eval`, then `layers`, then `native_probe apply`, `kernel`; a wrong type: `promote`; a lost digit: `--ref`; a wrong render: `render`, `widget`, `paint`; a misplaced cursor: `editor`; a look: `shot`), one pasteable example per command built from the outputs pasted in Tasks 4, 6, 8 and 9, the typed operand forms, `--def` and `@NAME`, `--test` and `--field`, `native_tests --case`, and how to read a value row and a graded row. No horizontal rules, no hard wrap.

- [ ] **Step 2: Check every example in `docs/probe.md` by running it.** Expected: each prints what the doc shows.

- [ ] **Step 3: Show the diff, wait for approval, commit** `docs/probe: which probe answers which question`.
