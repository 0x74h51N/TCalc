# Rational Overflow and intdiv Range Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An exact Rational result past int64 (#245) and an `intdiv` past $2^{53}$ (#252) are computed in BigReal instead of double.

**Architecture:** Two rules on the ops table rows, read by code that already runs. #245: a new per-row rule says when an op's answer on two Rationals is rational; `apply`'s catch reads it and retries in BigReal with `lift_to_big` instead of in double. #252: the `intdiv` row gets a `with_range` rule, so the existing `promote_big` lifts its operands before coerce turns them into doubles, and the existing BigReal kernel runs.

**Tech Stack:** C++20, Boost.Multiprecision (`BigReal`, `boost::rational`), the native test harness (`test_detail::with_case`), pytest e2e.

**Spec:** `docs/superpowers/specs/2026-11-16-rational-overflow-design.md`

## Global Constraints

- `coerce`, `promote_complex`, `promote_range`, the Rational kernels, both `intdiv` kernels and the formatter do not change. The double `intdiv` kernel keeps its `static_cast<long long>`.
- A Rational result inside int64 stays a Rational; `sqrt(2)` and `2^{1/2}` stay double; `0^{-1}`, `1/0` and `intdiv(7,0)` stay a math error.
- The `intdiv` bound is $2^{53}$ inclusive (`>=`), a named constant derived from `std::numeric_limits<double>::digits`.
- No bare numeric literal in `src/native/lib` other than 0 and 1 (tidy `avoid-magic-numbers`). No new file, class or layer.
- Test rows go into the existing tables (`tests.md`); exact values are the spec's, computed with Python integers. Any row outside the spec's lists whose type changes is reported to the human agent before its expected value is touched.
- No em dash anywhere. No commit without the human agent's approval of the diff; the docs (spec, this plan, findings, findings README) are committed last, in one commit. Never run clang-tidy.

## Review Focus

- A Rational retry whose BigReal rerun throws again (`0^{-1}`, `1/0`): it must stay the math error it is, not a different error. Existing `test_raises_math_error` rows cover it; Task 1 step 6 runs them.
- A small exact result whose denominator overflowed (`(1/3)^{40}`, `0.0000000001 * 0.0000000001`) now comes back BigReal, not double: Task 1 rows `pow(1/3, 40)` and the moved `rational-denominator-overflows-i64`.
- An irrational Rational op (`root(2,2)`, `2^{1/2}`, `log`) keeps its double retry: the existing `root(2, 2) is irrational` row and `pow-frac-exp-sqrt2`.
- `intdiv` at the exact bound: `9007199254740993` reads as $2^{53}$ and must widen, `9007199254740991` must not. Task 2 rows.
- `intdiv` with a zero divisor: the quotient is infinite, the rule holds, and the BigReal kernel's `require_nonzero` gives the math error. Task 2 row `intdiv(7,0)`.

### Task 1: The Rational retry widens into BigReal (#245)

**Files:**
- Modify: `src/native/lib/parser/pub/ops.hpp` (`OpRow`, the `with_*` builders, the Add/Sub/Mul/Div/Pow rows, a table and accessor beside `range_of`)
- Modify: `src/native/lib/eval/eval.cpp` (`apply`'s catch, about line 430)
- Test: `src/native/tests/unit/test_eval.cpp` (`range_promotion_arm_cases`, `range_promotion_value_cases`, the single test `apply :: mul of two small rationals ...`)
- Test: `tests/py/e2e/test_eval_e2e.py`

**Interfaces:**
- Produces: `using RationalAnswerRule = bool (*)(const Rational &x, const Rational &y);` in `ops.hpp` beside `RangeRule`; `OpRow::rational_answer` (after `range`); `constexpr OpRow with_rational_answer(OpRow r, RationalAnswerRule g);` `constexpr RationalAnswerRule rational_answer_of(OpId id);` (nullptr when the row names none), built like `range_of` from a `kRationalAnswers` table. Not `with_rational`: `without_rational` already exists and removes the Rat arm, a different thing.

- [ ] **Step 1: Native rows**

`range_promotion_arm_cases`, arm `Arm::Big` (`kI64Max` is `std::numeric_limits<std::int64_t>::max()`):

| id | op | operands |
|---|---|---|
| pow(3, 40) overflows the exact arm into BigReal | Pow | `Rational(3)`, `Rational(40)` |
| pow(1/3, 40) overflows the exact denominator into BigReal | Pow | `Rational(1, 3)`, `Rational(40)` |
| add(int64 max, 2) overflows the exact arm into BigReal | Add | `Rational(kI64Max)`, `Rational(2)` |
| mul(3037000500, 3037000500) overflows the exact arm into BigReal | Mul | `Rational(3037000500)` twice |
| div(int64 max, 1/2) overflows the exact arm into BigReal | Div | `Rational(kI64Max)`, `Rational(1, 2)` |

`range_promotion_value_cases`: the row `pow(2, 64) overflows the exact arm into a double` becomes `pow(2, 64) overflows the exact arm into BigReal` with `.expected = Value{BigReal("18446744073709551616")}`, and its comment above says the retry is in BigReal; add `pow(3, 40) is exact in BigReal` (`Rational(3)`, `Rational(40)`) to `BigReal("12157665459056928801")` and `mul(int64 max, int64 max) is exact in BigReal` (`Rational(kI64Max)` twice) to `BigReal("85070591730234615847396907784232501249")`.

The single test becomes `apply :: mul of two small rationals overflows the kernel, recovers as BigReal`: `arm_of(r) == Arm::Big` and `std::get<BigReal>(r) == BigReal("6.25e-20")`.

- [ ] **Step 2: e2e rows**

`test_native_eval_golden`, beside `pow-promotes-bigreal`, type `"BigReal"`: `10^{23}` `"1e+23"`, `10^{200}` `"1e+200"`, `10^{200}*10^{200}` `"1e+400"`, `10^{19}` `"1e+19"`, `3^{40}` `"1.215766545905693e+19"`, `(1/3)^{-40}` `"1.215766545905693e+19"`; ids `pow-ten-23-exact`, `pow-ten-200-exact`, `pow-ten-200-squared-exact`, `pow-ten-19-exact`, `pow-three-40-exact`, `pow-third-neg-40-exact`.

`test_bigreal_exact_results`, after the existing rows, under a one-line comment that a result past int64 is exact and `str` shows 16 digits, so a longer value is checked by a difference:

| expr | expected | id |
|---|---|---|
| 3^{40}-12157665459056928801 | 0 | pow-past-i64-exact |
| 9223372036854775807+2-9223372036854775809 | 0 | add-past-i64-exact |
| -9223372036854775807-2+9223372036854775809 | 0 | sub-past-i64-min-exact |
| 3037000500\*3037000500-9223372037000250000 | 0 | mul-past-i64-exact |
| (-3)^{41}+36472996377170786403 | 0 | pow-negative-past-i64-exact |
| 7^{23}-27368747340080916343 | 0 | pow-seven-23-exact |
| 9223372036854775807\*9223372036854775807-85070591730234615847396907784232501249 | 0 | mul-i64-max-squared-exact |
| 3^{40}\*3^{40}-147808829414345923316083210206383297601 | 0 | mul-past-i64-chain-exact |
| 9223372036854775807/(1/2)-18446744073709551614 | 0 | div-past-i64-exact |
| (1/3)^{40}\*3^{40} | 1 | pow-denominator-past-i64-cancels |

`TestRational::test_stays_rational`: `param("3^{39}", 4052555153018976267, 1, id="pow-i64-largest-power-of-three")`.

- [ ] **Step 3: Build, run, see the red**

Run: `make native-build && make native-test 2>&1 | grep -E "FAILED|PASSED" | tail -15` and `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q 2>&1 | tail -25`
Expected: every new native row and the two changed native tests fail; every new e2e row fails except `pow-i64-largest-power-of-three`, which passes (it guards the side that must not change). Record the failing ids.

- [ ] **Step 4: Implement**

In `ops.hpp`: the alias, the field (the five builders that copy a row positionally, `with_domain`, `with_range`, `with_trait`, `with_default` and `without_rational`, pass it through; `unary`, `binary` and the others set only the first three fields and need nothing), `with_rational_answer`, `kRationalAnswers` and `rational_answer_of`. One named rule `detail::always_rational` for Add, Sub, Mul and Div, and a lambda on the Pow row, `y.denominator() == 1`. `Rational` comes from `value.hpp`, already included.

In `apply`'s catch, after the `Arm::Rat` check: when `ops::rational_answer_of(id)` is not null and holds for `std::get<Rational>` of the two dispatched operands, lift them with `lift_to_big` and run the kernel again; otherwise the existing double retry runs unchanged. A second throw propagates. Rewrite the catch's comment for the two retries in one or two lines (the exact answer is rational, so the kernel can only have overflowed). The two operands are Rational whenever the rule is set: coerce lifts an Int64 beside a Rational, and a double or BigReal operand would have taken its own arm; `std::get` throws if that ever changes.

- [ ] **Step 5: Update the rows that pinned the double**

These pin today's double and become BigReal (the spec's list):

- Golden `pow-large-exp-stays-float` (`2^309`) becomes type `"BigReal"`, value `"1.042962419883257e+93"`, id `pow-large-exp-exact`.
- Golden `float-div-keeps-float` (`(10^307)/(10^306)`) becomes `"BigReal"`, `"10"`, id `div-of-big-powers-stays-big`.
- Golden `log-of-its-own-power-implicit-base` (`log(10^{21})`) becomes `"BigReal"`, `"21"`; its comment's last sentence names the BigReal it now gets.
- In `TestRational`, the rows `pow-i64-overflow`, `pow-i64-boundary-overflows`, `pow-neg-exp-i64-boundary-overflows`, `pow-frac-overflow` and `rational-denominator-overflows-i64` move from `test_downcasts_to_float` to `test_promotes_to_bigreal`, ids kept, the comment above the last one dropped.

Any other row that turns red is reported to the human agent with its output, not edited.

- [ ] **Step 6: Run, see green**

Run: `make native-build && make native-test 2>&1 | tail -5` and `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py tests/py/e2e/test_reductions_e2e.py -q 2>&1 | tail -5`
Expected: all pass, `test_raises_math_error` (`1/0`, `0^(-1)`) and `root(2, 2) is irrational` included.

Then, because `apply` is read by every area (`tests.md`), `make py-test 2>&1 | tail -15` and `make py-smoke 2>&1 | tail -5`. Expected: green. `make native-test` also runs the native smoke pin check; if a #249 pin (`smoke_stress.cpp`, `tests/py/smoke/test_smoke.py`) changes state, report it with the output and do not remove the pin.

- [ ] **Step 7: Grep the added native lines for numeric literals**

Run: `git diff -U0 src/native/lib | grep '^+' | grep -nE '[0-9]' | grep -v constexpr`
Expected: no literal other than 0 and 1.

- [ ] **Step 8: Format, show the diff, wait for approval, commit**

Run: `make cpp-format && make py-lint-fix`, then show `git diff` of the four files.

```bash
git add src/native/lib/parser/pub/ops.hpp src/native/lib/eval/eval.cpp src/native/tests/unit/test_eval.cpp tests/py/e2e/test_eval_e2e.py
git commit -m "fix/eval: an exact result past int64 retries in BigReal"
```

### Task 2: intdiv widens before it runs (#252)

Done in 5f848d4, then replaced after review: Int64 and Rational operands run an exact `intdiv` kernel that returns int64, and the range rule guards only the double kernel (spec section 3; findings `rational-overflow.md`, 2026-11-17).

**Files:**
- Modify: `src/native/lib/parser/pub/ops.hpp` (the `detail` constants, a rule beside `power_needs_big`, the `IntDiv` row, `#include <limits>`)
- Test: `src/native/tests/unit/test_eval.cpp`, `tests/py/e2e/test_eval_e2e.py`

**Interfaces:**
- Consumes: `with_range`, `RangeRule`, `promote_big` (unchanged).
- Produces: `inline constexpr double kExactIntBound` in `ops.hpp`'s `detail` ($2^{53}$, `static_cast<double>(std::uint64_t{1} << std::numeric_limits<double>::digits)`); `inline bool quotient_needs_big(double x, double y)`, true when $|x|$, $|y|$ or $|x/y|$ is `>= kExactIntBound`.

- [ ] **Step 1: Native rows**

`range_promotion_arm_cases`, arm `Arm::Big`: `intdiv(int64 max, 1) widens into BigReal` (Int64 `kI64Max`, Int64 `1`), `intdiv(1e19, 3) widens into BigReal` (`1e19`, `3.0`), `intdiv(2^53+1, 1) widens at the bound` (Int64 `9007199254740993`, Int64 `1`).

`range_promotion_value_cases`: `intdiv(int64 max, 2^40) is exact in BigReal` (Int64 `kI64Max`, Int64 `1099511627776`) to `BigReal("8388607")`; `intdiv(-int64 max, 2) truncates in BigReal` (Int64 `-kI64Max`, Int64 `2`) to `BigReal("-4611686018427387903")`; `intdiv(7, 2) stays an integer` to `Value{std::int64_t{3}}`; `intdiv(2^53-1, 1) stays an integer` (Int64 `9007199254740991`, Int64 `1`) to `Value{std::int64_t{9007199254740991}}`.

- [ ] **Step 2: e2e rows**

`test_native_eval_golden`, type `"BigReal"`: `intdiv(1e19,1)` `"1e+19"`, `intdiv(1e300,1)` `"1e+300"`, `intdiv(9223372036854775807,1)` `"9.223372036854776e+18"`, `intdiv(1e19,3)` `"3.333333333333333e+18"`; ids `intdiv-past-i64-widens`, `intdiv-huge-widens`, `intdiv-i64-max-widens`, `intdiv-past-i64-third`. Type `"int"`: `intdiv(7,2)` `"3"`, `intdiv(-7,2)` `"-3"`, `intdiv(9007199254740991,1)` `"9007199254740991"`; ids `intdiv-small-stays-int`, `intdiv-negative-truncates`, `intdiv-below-bound-stays-int`.

`test_bigreal_exact_results`:

| expr | expected | id |
|---|---|---|
| intdiv(9223372036854775807,1)-9223372036854775807 | 0 | intdiv-i64-max-exact |
| intdiv(1e19,3)-3333333333333333333 | 0 | intdiv-past-i64-exact |
| intdiv(-1e19,3)+3333333333333333333 | 0 | intdiv-negative-past-i64-exact |
| intdiv(9007199254740993,1)-9007199254740993 | 0 | intdiv-bound-exact |
| intdiv(9223372036854775807,1099511627776) | 8388607 | intdiv-large-operand-small-quotient |
| intdiv(-9223372036854775807,2)+4611686018427387903 | 0 | intdiv-negative-truncates-exact |

`TestRational::test_raises_math_error`: `param("intdiv(7,0)", id="intdiv-by-zero")`.

- [ ] **Step 3: Build, run, see the red**

Same commands as Task 1 step 3. Expected: the BigReal rows of both tables fail; the `int` rows, `intdiv(2^53-1, 1) stays an integer`, `intdiv(7, 2) stays an integer` and `intdiv-by-zero` pass. If `int` golden values print differently from `str` of a Python int, fix the expected text to what today prints and say so.

- [ ] **Step 4: Implement**

The constant and `quotient_needs_big` in `ops.hpp`'s `detail`, with a one-line why (a double holds every integer only below $2^{53}$, and the operands are read through `as_double`, where $2^{53}+1$ is already $2^{53}$). The `IntDiv` row becomes `with_range(binary(OpId::IntDiv, TCALC_CALL(intdiv)), [](double x, double y) { return detail::quotient_needs_big(x, y); })`, like Pow's.

- [ ] **Step 5: Run, see green**

Same commands as Task 1 step 6, plus `make native-test` covering `test_arithmetic.cpp`'s `intdiv` cases, which call the kernels directly and do not change. Expected: all pass.

- [ ] **Step 6: Literal grep, format, show the diff, wait for approval, commit**

Task 1 step 7's grep, then `make cpp-format && make py-lint-fix` and the diff.

```bash
git add src/native/lib/parser/pub/ops.hpp src/native/tests/unit/test_eval.cpp tests/py/e2e/test_eval_e2e.py
git commit -m "fix/eval: intdiv past 2^53 runs in BigReal"
```

### Task 3: Cases through the app, docs commit

**Files:**
- Commit: `docs/superpowers/specs/2026-11-16-rational-overflow-design.md`, `docs/superpowers/plans/2026-11-17-rational-overflow.md`, `docs/superpowers/findings/rational-overflow.md`, `docs/superpowers/findings/README.md`

- [ ] **Step 1: Run the issues' cases through the app path**

The rows of #245 and #252 through the editor's plain text, `evaluate_branch` and `format_result` (the scratch `e2e_budget.py` probe or the same in a one-off script). Record them in the findings under a dated entry; they become the PR's Input | Expected | Result table, with `3^{40}` and `intdiv(9223372036854775807,1)` showing 16 digits and a reference to #244.

- [ ] **Step 2: Check the docs against the code as built**

Spec, findings and this plan against the Task 1 and 2 diff; any name, value or claim that changed is fixed now. No em dash (U+2014).

- [ ] **Step 3: Show the diff, wait for approval, commit**

```bash
git add docs/superpowers/specs/2026-11-16-rational-overflow-design.md docs/superpowers/plans/2026-11-17-rational-overflow.md docs/superpowers/findings/rational-overflow.md docs/superpowers/findings/README.md
git commit -m "docs/eval: rational overflow and intdiv range spec, plan and findings"
```
