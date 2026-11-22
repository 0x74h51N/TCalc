# Result Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Results are shown from their own digits (exact values at 20, doubles at 16, no zero padding in the digits) and a fraction is recalled as itself (#244, #235, #255).

**Architecture:** A native `tcalc::decimal_text(value, digits)` in `value.hpp` writes an int64, a Rational, a BigReal or a BigComplex from the exact value with `to_big` and Boost's `str(digits)`. `format_result` calls it for the display and passes every display text through one helper (thousands separators); its default output writes text that reads back as the same value.

**Tech Stack:** C++20, Boost.Multiprecision, pybind11, Python 3.14, pytest.

**Spec:** `docs/superpowers/specs/2026-11-22-result-text-design.md`

## Global Constraints

- New code, approved by the human agent: `decimal_text` (native) and one display helper in `utils.py` that replaces `fmt_real`'s grouping lines. Nothing else new.
- No `to_double()`, `float()` or `int()` of a native value in Python.
- `decimal_text` has one overload per arm, bound with `py::arg`; the `1e10` threshold is a named `constexpr`.
- `RESULT_DIGITS = 20` is the one digit constant in `utils.py`.
- Unit tests import only `format_result` and use fakes.

## Review Focus

- MR after `^`: `2^(1/3)`, not `2^1/3`.
- A collection keeps default item text: `[10000000000, 2]` shows `[10000000000, 2]`.
- The history, the memory bar and the result line show the display text.
- A BigComplex with imaginary part 1 shows `1i` (the double complex shows `i`); checked, not changed.
- An exponent of four digits or more is not grouped: `1e+1234`.

### Task 1: native `decimal_text`

**Files:**
- Modify: `src/native/lib/value.hpp` (beside `to_big`, lines 114-170), `src/native/python/bindings/bind_eval.cpp`
- Test: `src/native/tests/unit/test_eval.cpp` (beside `to_big`'s tests, 200-224)

- [ ] **Step 1:** A typed table (`input` as text of the value, `digits`, `expected`, `id`) with `test_detail::with_case`, one table per signature: int64 `10000000000` is `1e+10`, `-10000000000` is `-1e+10`, `12345678900` is `1.23456789e+10`, `12345678901` is `12345678901`, `9999999999` is `9999999999`; Rational `1/3` is `0.33333333333333333333`, `9007199254740993/2` is `4503599627370496.5`, `1/10000000` is `1e-07`, `9223372036854775807/3` is `3074457345618258602.3`; BigReal `1e400/3` is `3.3333333333333333333e+399`; BigComplex `0+1e400i` is `1e+400i`, `0+0i` is `0`, `-1e800+0i` is `-1e+800`, `0-5e-201i` is `-5e-201i`, `1234+3.333e199i` keeps both parts.
- [ ] **Step 2:** `make native-test`. Expected: compile error, `decimal_text` not declared.
- [ ] **Step 3:** Write the overloads as the spec says (count the digits before `e`, trailing zeros dropped; BigComplex parts through `BigReal(c.real())`). Bind them in `bind_eval.cpp`. `make native-build`.
- [ ] **Step 4:** `make native-test`. Expected: PASS.

### Task 2: `format_result`

**Files:**
- Modify: `src/tcalc/ui/controller/utils.py`
- Test: `tests/py/unit/ui/test_format_result.py`, `tests/py/e2e/ui/test_format_result_e2e.py`

- [ ] **Step 1:** Unit: a fake `decimal_text` in the fake `calc_native`, `FakeRational.__str__`, `to_double` removed. Changed rows: `int past a double` default `10000000000000001`; `whole rational stays exact` default `10000000000000001`; `fraction` default `(1/4)`; `large float` `1e+11`; `small float` `5.960464477539062e-08`; `big real` and `big complex` give the fake's text. New rows: display of an `int`, a `Rational`, a `BigReal`, a `BigComplex` gives the fake's text through the helper (fake `1234+5678.5e+12i` shows `1,234+5,678.5e+12i`). e2e `FORMAT_CASES` (exact `==`): every row of the spec's Cases table with `group=True`; `exact-fraction-decimal` becomes `(1/4)`, `exact-int-past-double` `10000000000000001`, `int64-max-literal` `9223372036854775807`. `9999999999` is a boundary row that passes today. A test `test_default_output_reads_back` (its own function: it evaluates the text again), rows `1/3`, `-2/7`, `9007199254740993/2`, `10000000000`, `2^{40}`, `10^{16}+1`, `1e400i`: `str(_eval(f"{format_result(_eval(expr))}-({expr})"))` is `0` or `0+0i` (the native types have no `==`).
- [ ] **Step 2:** Run both files. Expected: the new and changed rows FAIL.
- [ ] **Step 3:** `format_result`: default and display branches as the spec says; `fmt_real` writes `.15e` with trailing zeros dropped; the helper replaces lines 95-98 and runs on every display text.
- [ ] **Step 4:** Run both files and `tests/py/e2e/ui/test_controller_status.py`, `tests/py/e2e/ui/test_result_widget.py`. Expected: PASS.

### Task 3: the whole check

- [ ] **Step 1:** `make stub-gen`, `make typecheck`, `make py-lint-fix`, `make cpp-format`. Expected: clean.
- [ ] **Step 2:** `make py-test`. Expected: no failure beyond the known xfails.
- [ ] **Step 3:** Run the app in the flat and the math mode: `1/3`, MS, MR, `*3-1` is `0`; `1/3` `=` then `*3-1` is `0`; `2^` then MR is `2^(1/3)`; `10000000000` and `1e10` show `1e+10`; `1e400i` shows `1e+400i`; look at `(1/3)` in the math mode.
- [ ] **Step 4:** A finding in `docs/superpowers/findings/result-text.md` with the measured rows, and its line in the findings index.
- [ ] **Step 5:** Stop: show the diff to the human agent; no commit without approval.
