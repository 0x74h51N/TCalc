# INT64_MIN Reciprocal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the reciprocal of a Rational whose numerator is `-9223372036854775807-1` raises a `CalculatorError` the retry catches, so every #249 case gives a value instead of `Invalid inputs`.

**Architecture:** the two kernel sites (`Calculator::pow`, `Calculator::root`) take the reciprocal through the existing `Calculator::div`, which narrows and raises `math_error()`; the real-first rewrite in `apply`, which runs outside the retry's `try`, skips the rewrite when the degree's reciprocal does not fit, so the op takes the ordinary path.

**Tech Stack:** C++ native core (`src/native/lib/`), pybind11 binding, pytest e2e.

**Spec:** `docs/superpowers/specs/2026-11-18-int64-min-reciprocal-design.md`

## Global Constraints

- No header, helper, function or class is added or renamed; no check is added beyond the one in Task 3, whose input is `(-8)⌄(M/3)`.
- Tests first: every new row is seen red before its fix.
- Expected values are the spec's table, not the output after the fix. If the run after a fix gives another type, or a value off beyond what its type holds, stop and report before any row changes.
- `make native-build` after every C++ change; never run clang-tidy.
- No commit without the human agent's approval of the diff; run `make cpp-format` and `make py-lint-fix` before it.
- M below is written out as `-9223372036854775807-1` in every row.

## Review Focus

- A reciprocal that fits keeps the real-first rewrite: `(-8)⌄(1/3)` stays `Rational -512` (Task 3, `test_stays_rational`), and the existing `root-reciprocal-degree-*` rows stay green.
- A negative exponent that fits stays exact: the native `pow :: negative exponent` row (`(2/3)^(-2)`) and the e2e `zero-to-neg-power` math error stay green (Task 2, `make native-test` and the e2e file).
- A reciprocal one step inside int64 stays exact: `(-9223372036854775807)⁻¹` is `Rational(-1, 9223372036854775807)` (measured on b00725b), a row in `test_stays_rational` (Task 1), green before and after.
- No other `Rational(den, num)` swap is left: Task 2's last step greps `src/native/lib` for `denominator(), .*numerator()`; any hit besides `eval.cpp:423` (Task 3) is reported, not fixed.
- The smoke run catches any op the fix sends to a new abort: `make py-smoke` in Task 2.

### Task 1: The e2e rows, red

**Files:**
- Modify: `tests/py/e2e/test_eval_e2e.py`, the `test_native_eval_golden` table (head at line 47), a new group after the `root-reciprocal-degree-*` rows (around line 362); `TestRational::test_stays_rational`

**Interfaces:**
- Produces: 14 rows whose ids end in `recip-i64-min`, selected by `-k recip-i64-min`.

- [ ] **Step 1: Write the rows**

The row type is the arm the retry reads (spec, "What the user sees"); a complex is `(real, imag)`. One comment over the group: the float and complex checks are `pytest.approx`, so the digits a double drops below `1e-16` in the roots near 1 are #231.

| expr | type | value | id |
|---|---|---|---|
| (-9223372036854775807-1)^(-1) | BigReal | "-1.084202172485504e-19" | pow-minus-one-recip-i64-min |
| (-9223372036854775807-1)⁻¹ | float | -1.0842021724855044e-19 | recip-recip-i64-min |
| ((-9223372036854775807-1)/3)⁻¹ | float | -3.2526065174565133e-19 | recip-of-third-recip-i64-min |
| (1)⌄(-9223372036854775807-1) | float | 1.0 | root-of-one-recip-i64-min |
| (-1)⌄(-9223372036854775807-1) | complex | (1.0, -3.4061215800865546e-19) | root-of-minus-one-recip-i64-min |
| (0.5)⌄(-9223372036854775807-1) | float | 1.000000000000000000075151 | root-of-half-recip-i64-min |
| (1/3)⌄(-9223372036854775807-1) | float | 1.000000000000000000119112 | root-of-third-recip-i64-min |
| (9223372036854775807)⌄(-9223372036854775807-1) | float | 0.9999999999999999952654764 | root-of-i64-max-recip-i64-min |
| (-9223372036854775807-1)⌄(-1) | float | -1.0842021724855044e-19 | root-degree-minus-one-recip-i64-min |
| (-9223372036854775807-1)⌄(-9223372036854775807-1) | complex | (0.9999999999999999952654764, -3.4061215800865546e-19) | root-of-itself-recip-i64-min |
| (-9223372036854775807-1)^(-1/3) | BigReal | "-4.76837158203125e-07" | pow-minus-third-recip-i64-min |
| ((-9223372036854775807-1)/3)⌄(-8) | complex | (0.0045148599892078299, -0.0018701162397455287) | root-of-third-degree-minus-eight-recip-i64-min |
| (8)⌄((-9223372036854775807-1)/3) | float | 0.9999999999999999993236395 | root-degree-third-recip-i64-min |
| (-8)⌄((-9223372036854775807-1)/3) | complex | (0.9999999999999999993236395, -1.021836474025966376e-18) | root-negative-degree-third-recip-i64-min |

Beside them, in `test_stays_rational`: `param("(-9223372036854775807)⁻¹", -1, 9223372036854775807, id="recip-of-minus-i64-max-stays-exact")`.

- [ ] **Step 2: Run them red**

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -k "recip-i64-min or recip-of-minus-i64-max" -q`
Expected: `14 failed, 1 passed`; each failure is `ValueError: bad rational: non-zero singular denominator`, the pass is `recip-of-minus-i64-max-stays-exact`.

### Task 2: The kernel sites, pow and root

**Files:**
- Modify: `src/native/lib/calc/arithmetic.cpp:196-198` (`Calculator::pow`), `:205` (`Calculator::root`)
- Modify: `tests/py/smoke/test_smoke.py:49-64` (`SMOKE_PINS`)
- Modify: `docs/superpowers/findings/int64-min-reciprocal.md`

**Interfaces:**
- Consumes: `Rational Calculator::div(const Rational &a, const Rational &b) const` (`arithmetic.cpp:139`), unchanged.

- [ ] **Step 1: `Calculator::pow`**: inside the existing `if (neg_exp)`, `return div(Rational(1), Rational(result));` replaces the swap.
- [ ] **Step 2: `Calculator::root`**: `const Rational inv = div(Rational(1), b);` replaces `const Rational inv(b.denominator(), b.numerator());`.
- [ ] **Step 3: Build**: `make native-build`, then `make native-test`. Expected: the build has no new warning; native tests all pass.
- [ ] **Step 4: Run the rows**: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -k recip-i64-min -q`. Expected: `13 passed, 1 failed`; the failure is `root-negative-degree-third-recip-i64-min`, still `ValueError` (the `eval.cpp:423` site, Task 3). Any other failure: stop and report.
- [ ] **Step 5: Whole e2e file**: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q`. Expected: only `root-negative-degree-third-recip-i64-min` fails.
- [ ] **Step 6: Smoke, red then green**: `make py-smoke`. Expected: the 16 #249 pins fail as `XPASS(strict)` and nothing else fails. Remove the 16 `"#249"` entries from `SMOKE_PINS`, run `make py-smoke` again. Expected: passes.
- [ ] **Step 7: Grep for another swap**: `grep -rn "denominator(), .*numerator()" src/native/lib`. Expected: `eval.cpp:423` only (Task 3).
- [ ] **Step 8: Findings**: add a dated entry with the type and value each row returned, from Step 4's run with `-v`.
- [ ] **Step 9: Commit, after the human agent approves the diff**: `make cpp-format`, `make py-lint-fix`, then `git add src/native/lib/calc/arithmetic.cpp tests/py/e2e/test_eval_e2e.py tests/py/smoke/test_smoke.py` and `git commit -m "fix/calc: the reciprocal of int64 min in pow and root retries instead of escaping"`.

### Task 3: The real-first rewrite in apply

**Files:**
- Modify: `src/native/lib/eval/eval.cpp:419-424`
- Modify: `tests/py/e2e/test_eval_e2e.py`, `TestRational::test_stays_rational` table
- Modify: `docs/superpowers/findings/int64-min-reciprocal.md`

**Interfaces:**
- Consumes: `calc_detail::WideRational`, `calc_detail::widen(const Rational &)`, `calc_detail::narrow(const WideRational &) -> std::optional<Rational>` (`calc/internal/helpers.hpp:388-407`), reached through `parser/pub/ops.hpp`.

- [ ] **Step 1: The other branch's row**: add `param("(-8)⌄(1/3)", -512, 1, id="root-reciprocal-degree-stays-exact")` to `test_stays_rational`. Run `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -k "root-reciprocal-degree or recip-i64-min" -q`. Expected: the new row and the three `root-reciprocal-degree-*` rows pass, `root-negative-degree-third-recip-i64-min` fails.
- [ ] **Step 2: The rewrite**: in the `Trait::InverseDegree` branch, the degree's reciprocal is `calc_detail::narrow(calc_detail::WideRational(1) / calc_detail::widen(*e))`, and `return apply(c, OpId::Pow, {args[0], Value{*inv}}, unit);` runs only when it holds a value; otherwise the code goes on to the `RootExponent` check and the ordinary path.
- [ ] **Step 3: Build and run**: `make native-build`, `make native-test`, then `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q`. Expected: all pass. If `root-negative-degree-third-recip-i64-min` gives another type or value, stop and report.
- [ ] **Step 4: Smoke**: `make py-smoke`. Expected: passes.
- [ ] **Step 5: Findings**: the row's type and value in the dated entry.
- [ ] **Step 6: Commit, after the human agent approves the diff**: `make cpp-format`, `make py-lint-fix`, `git add src/native/lib/eval/eval.cpp tests/py/e2e/test_eval_e2e.py`, `git commit -m "fix/eval: a root degree whose reciprocal is past int64 skips the real-first rewrite"`.

### Task 4: The docs, one commit

**Files:**
- `docs/superpowers/specs/2026-11-18-int64-min-reciprocal-design.md`, this plan, `docs/superpowers/findings/int64-min-reciprocal.md`, `docs/superpowers/findings/README.md`

- [ ] **Step 1: Read the spec and the findings against what Tasks 2 and 3 measured**; a value or type the run changed is corrected in the same commit.
- [ ] **Step 2: Commit, after the human agent approves the diff**: `git add` the four files by name, `git commit -m "docs/superpowers: int64 min reciprocal spec, plan and findings"`.
