# Native abort and smoke runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No input aborts the process: gcd and lcm refuse a value int64 cannot hold, and two smoke runs (native over `apply`, Python over the production path) name every case that aborts or freezes.

**Architecture:** `to_integer` gains a range check. A native smoke suite drives every kernel row of the ops table with edge Values in forked children; a Python smoke run drives built expression strings through the editor text, `tokenize`, `evaluate_branch` and `format_result` in worker processes with the app's deadline. Both name a dead or stuck case and go on.

**Tech Stack:** C++23, Boost.Multiprecision, POSIX `fork`/`poll`/`waitpid`, pybind11, Python 3.14, pytest, PySide6 offscreen, `subprocess` workers over JSON lines.

**Spec:** `docs/superpowers/specs/2026-11-16-native-abort-smoke-design.md`

## Global Constraints

- An input that aborted shows an error instead; its right answer belongs to its own issue (#247 for gcd and lcm).
- No new helper, error kind or message for the refusal: the existing `calc_detail::math_error()`.
- A wrong number seen on the way is not fixed: it goes to its open issue (#240, #241, #242, #244, #245, #247) or a new one.
- A freeze is #248's: pinned with the issue and the date; a pinned case that passes fails the run.
- The Python run uses the app's own budget constant, never a second `500`.
- No commit without the human agent's approval of the diff; never run clang-tidy; no em dash anywhere.
- Before fixing an abort the runs find (Task 4), explain its cause and fix to the human agent and wait.

## Review Focus

- A case that aborts on its first operand set: the child restarts at the next case, not at the same one (no loop).
- A child that dies before announcing any case (setup failure): reported as a setup failure, not blamed on case 0.
- The Python worker's own import or `QApplication` failure: reported once, not once per case.
- A pinned case id that no longer exists in the built case list (an op renamed): fails the run.
- Output size: a run with hundreds of failures prints each failure once, as its own case, and the run still ends.

### Task 1: Native smoke run over `apply`

**Files:**
- Create: `src/native/tests/internal/smoke_helpers.hpp`: the shared smoke rule. `run_guarded(fn) -> SmokeResult` classifies how a call ended (`SmokeOutcome::Returned`, `MathError`, `OtherException`); `smoke_allow_math_error` moves here from `smoke_stress.cpp` and uses it; `run_isolated(count, limit_ms, run_case) -> IsolatedRun` runs cases in forked children with the same rule and reports `CaseFailure{index, CaseFault::Abort|Freeze|Exception, detail}`. A new file, because the in-process and the forked runner share one rule; its argument is that rule, kept in one place.
- Modify: `src/native/tests/smoke/smoke_stress.cpp`: the ops sweep joins the existing suite as `smoke_ops(ctx)`, called at the end of `smoke_stress`. No new suite, no `main.cpp` or `CMakeLists.txt` change.

**Interfaces:**
- Produces: `smoke_helpers.hpp` (`run_guarded`, `smoke_allow_math_error`, `run_isolated`).

- [ ] **Step 1: Write the suite**

  - Cases: every `OpId` in `[0, ops::kOpCount)` with `ops::kernel_of(id) != nullptr`. Operand count from `ops::op_spec(id)`: `Arity::Binary`, or a `call_arity` of 2, takes 2; a variadic op (`is_variadic`) takes 1 Collection; otherwise 1.
  - Edge Values, exactly the spec's list (§2): Int64 `0`, `1`, `-1`, INT64_MAX, INT64_MIN; Double `0.0`, `-0.0`, `0.5`, `1e19`, `0x1p63`, `1e308`, `std::numeric_limits<double>::denorm_min()`, `inf`, `-inf`, `nan`; Rational `1/3`, `INT64_MAX/1`, `1/INT64_MAX`; BigReal `"1e400"`, `"1e-400"`; Complex `(inf, 0)`, `(0, nan)`; BigComplex `(1e400, 0)` and one with a `nan` part; Collection: an empty List and a Point of two. `CollectionItem` has no Rational arm, so no collection carries a Rational edge.
  - A one-operand op takes each edge; a two-operand op every ordered pair; a variadic op takes a one-item List of each non-Rational scalar edge, a two-item List of each ordered pair of them, the empty List and the Point. One List of all the edges would hide an abort behind an earlier item that throws (`to_integer` throws on `nan` before `std::gcd` ever sees INT64_MIN).
  - Case id: `"<symbol> :: <arm>(<edge>)[, <arm>(<edge>)]"`, built from `op_spec(id)->symbol` and the edge's short name.
  - Runner: the parent forks a child that runs cases from index `k` on; before each case the child writes its index to a pipe. The child never touches `ctx` or stdout, sets `RLIMIT_CORE` to 1 (Linux ignores 0 when `core_pattern` is a pipe such as systemd-coredump, and the dump then outlasts the case limit, so an abort reads as a freeze), and ends with `_exit`, so the parent's buffered test output is not written twice. The child calls `apply(c, id, args, AngleUnit::RAD)`; a `CalculatorError` passes; any other exception writes a failure record (index and `what()`) to the pipe and goes on. The parent `poll`s the pipe with a 1000 ms limit per case: on child exit by a signal, or on the limit, it records the last announced case as `abort (signal N)` or `freeze`, kills and reaps the child, and forks a new one at the next index. A child that dies before announcing a case is a setup failure.
  - Pins: `const std::vector<SmokePin> kSmokePins` with `.case_id`, `.issue`, `.date`. A pinned case that fails passes; a pinned case that passes, or a pin whose id is not among the cases, fails.
  - Report: one `test_detail::with_case(ctx, "ops :: <case id>", ...)` per case, so the suite total counts every `apply` call and a failure names its case, its fault (`abort signal N`, `freeze`, `exception <what>`). A pinned case expects its failure in the same case; a pin with no case fails `ops :: pins`. No raw `TEST` macros.

- [ ] **Step 2: Build and run it on master's kernels**

  Run: `make native-build && make native-test > $W/smoke1.log 2>&1; grep -E "ops ::|FAILED|PASSED" $W/smoke1.log | tail -40`
  Expected: red on `gcd` and `lcm` with `abort (signal 6)` for the cases with `1e19`, `0x1p63` and INT64_MIN beside another operand; `freeze` on `nPr` of INT64_MAX with INT64_MAX (measured: `nCr` of the same pair returns). Record the full list of failing cases and the run time in the findings file, then report both to the human agent before going on.

- [ ] **Step 3: Pin the freezes**

  Add a `kSmokePins` row per `nPr` freeze case with `.issue = "#248"` and `.date = "2026-11-16"`. A freeze of another op is reported to the human agent first; it is pinned to #248 only if the cause is the same (a kernel loop the deadline does not reach).
  Run: `make native-test`. Expected: red only on the gcd and lcm aborts.

- [ ] **Step 4: Commit (after the human agent approves the diff)**

  `git add src/native/tests/internal/smoke_helpers.hpp src/native/tests/smoke/smoke_stress.cpp` then `test/native: smoke run of every kernel over edge values`. The suite is red on gcd and lcm at this commit; Task 2 turns it green, before any push.

### Task 2: `to_integer` refuses what int64 cannot hold (#246)

**Files:**
- Modify: `src/native/lib/calc/number_theory.cpp:18-27`
- Test: `src/native/tests/unit/test_number_theory.cpp`

- [ ] **Step 1: Write the failing rows**, beside `gcd :: non-integer rejected`:

```cpp
TEST_CASE(ctx, "gcd :: a double past int64 rejected", {
    EXPECT_THROWS(ctx, c.gcd(list({1e19, 3.0})));
    EXPECT_THROWS(ctx, c.gcd(list({0x1p63, 2.0})));
});
TEST_CASE(ctx, "gcd/lcm :: INT64_MIN rejected", {
    const auto lo = std::numeric_limits<std::int64_t>::min();
    EXPECT_THROWS(ctx, c.gcd(list({lo, std::int64_t{2}})));
    EXPECT_THROWS(ctx, c.lcm(list({lo, std::int64_t{1}})));
});
TEST_CASE(ctx, "gcd :: INT64_MIN + 1 accepted", {
    const auto lo = std::numeric_limits<std::int64_t>::min() + 1;
    EXPECT_EQ(ctx, std::get<std::int64_t>(c.gcd(list({lo, std::int64_t{1}}))), 1LL);
});
```

- [ ] **Step 2: Run them**

  Run: `make native-build && make native-test`
  Expected: the test process aborts at `gcd :: a double past int64 rejected` with the `__abs_r` assertion (the abort is the red).

- [ ] **Step 3: Implement**

  In `to_integer`, an Int64 equal to INT64_MIN, and a whole double with `std::fabs(d) >= 0x1p63`, call `calc_detail::math_error()`. The range test runs before `std::llround`.

- [ ] **Step 4: Run them, and the smoke run**

  Run: `make native-build && make native-test`
  Expected: all PASSED; the `ops :: gcd` and `ops :: lcm` cases green.

- [ ] **Step 5: Commit (after approval)**

  `fix/calc: gcd and lcm refuse a value int64 cannot hold`

### Task 3: Python smoke run over the production path

**Files:**
- Modify: `src/tcalc/ui/app.py:42`: the budget becomes `EVAL_TIME_BUDGET_MS = 500`, a module constant beside `run_app`, which `run_app` passes.
- Modify: `tests/py/helpers.py`: gains `editor_canonical(expr: str) -> str`, the editor round trip moved out of `_canonicalize` in `tests/py/e2e/test_eval_e2e.py` (the raw path for a `_{` form included). `_canonicalize` keeps its `CANON_LOG` append and calls it. This move is named here, so the plan carries it.
- Create: `tests/py/smoke/__init__.py`, `tests/py/smoke/test_smoke.py`, `tests/py/smoke/worker.py`. A new test directory: a file under `tests/py/e2e/` would join `make py-test`, which the spec keeps it out of.
- Modify: `makefile` (target `py-smoke: QT_QPA_PLATFORM=offscreen PYTHONPATH=src $(PY) -m pytest tests/py/smoke $(PYTEST_ARGS)`), `.github/workflows/ci.yml` (job `py-smoke`, the same `needs`, `if` and native artifact steps as `py-test`, running `make py-smoke`; added to `ci-ok`'s `needs`).

**Interfaces:**
- Consumes: `EVAL_TIME_BUDGET_MS`, `editor_canonical`, `calc_native.op_table()` (`symbol`, `arity`, `call_arity`, `is_variadic`), `evaluate_branch`, `tokenize`, `format_result`.

- [ ] **Step 1: Move `editor_canonical` and the budget constant**

  Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/test_eval_e2e.py -q`
  Expected: the same count as before the move, all passed.

- [ ] **Step 2: Write the run**

  - Forms by `arity`: Binary `({a}){sym}({b})`; Postfix `({a}){sym}`; Unary with `call_arity` 1 `{sym}({a})`, with 2 `{sym}({a},{b})`; variadic `{sym}({a},{b})` and `{sym}({list})`. The symbol is the table's own (measured: `√4`, `2·3`, `5⁻¹`, `u-(2)`, `x̄(1,2)` all evaluate).
  - LaTeX forms: `\frac{{a}}{{b}}`, `\sqrt{{a}}`, `\root{{a}}{{b}}`, `{a}^{{b}}`, `log_{{a}}{b}`, `\sum_{n=1}^{{a}} n`, `\prod_{n=1}^{{a}} n`.
  - Operand texts, exactly the spec's list (§3); `{list}` is `[0,1e400,-1]`, a point `(1,2)`, a nested `[[1],[2]]`, an empty `[]`.
  - A case id is its input string.
  - Workers: `tests/py/smoke/worker.py`, run as `python -m tests.py.smoke.worker` from the repo root, reads its case list as JSON on stdin and writes `{"start": i}` before each case, `{"error": i, "exc": repr(exc)}` for an exception other than `tcalc.errors.CalculatorError`. It sets `RLIMIT_CORE` to 1, makes one `QApplication`, sets the budget from `EVAL_TIME_BUDGET_MS`, and per case arms `faulthandler.dump_traceback_later(4 * budget, exit=True)`: a C thread, so a freeze inside a native call that holds the GIL still ends the worker, with exit code 1. Not `multiprocessing`: its default start method on Python 3.14 is `forkserver`, which would have to import the test module in the child.
  - Parent: `os.cpu_count()` interleaved chunks on a `ThreadPoolExecutor`, each a loop of `subprocess.run` over the remaining cases. Exit 0 ends the chunk; exit 1 is a `freeze`, a negative code an `abort signal N`, both on the last started case, and the next worker starts after it. A worker that ends before its first case raises with its stderr.
  - Report: a module fixture runs every case once; `test_case` is parametrized over the cases (id = the input string) and asserts the case has no fault. Pins: `SMOKE_PINS: dict[str, tuple[str, str]]` (case to issue and date) become `pytest.mark.xfail(strict=True)`, so a pinned case that passes fails; `test_pins_name_cases` fails on a pin that names no case.

- [ ] **Step 3: Run it**

  Run: `make py-smoke > $W/pysmoke.log 2>&1; tail -60 $W/pysmoke.log`
  Expected: green apart from cases to pin as in Task 1 Step 3 (the gcd and lcm aborts are already fixed by Task 2). Record the case count, failures and run time in the findings file and report them to the human agent.

- [ ] **Step 4: Commit (after approval)**

  `test/py: smoke run of the production path` with the files above.

### Task 4: Triage what the runs found

- [ ] **Step 1: Sort every failure from Task 1 and Task 3** into abort, freeze, and (seen on the way) wrong number, in the findings file `docs/superpowers/findings/native-abort.md`.
- [ ] **Step 2: Report** the list to the human agent: for each abort, its cause and the planned fix; each freeze to #248 as a comment with its pin; each wrong number to its open issue or a proposed new one. Wait for approval.
- [ ] **Step 3: Fix each approved abort** as Task 2 did: a red unit row first, the fix, `make native-test` and `make py-smoke` green, one commit per cause after approval.

### Task 5: Docs

- [ ] **Step 1:** Close the findings entry with what was fixed, pinned and reported, with the commands and counts.
- [ ] **Step 2: Commit (after approval)** the spec, this plan and the findings in one docs commit: `docs/native: abort smoke spec, plan and findings`.
