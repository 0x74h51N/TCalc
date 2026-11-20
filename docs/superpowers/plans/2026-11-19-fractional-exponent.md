# Power from its Exact Fractional Exponent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a power refused by the exact kernel at a non-whole `Rational` exponent is computed from `a/c` and `p/q`, each part within 1 ulp and a zero part `+0`, for `Pow`, `Root` and `Pow10` (#231).

**Architecture:** two `Calculator` methods compute the power from exact operands: the corrected pow (`pow` on the rounded base and exponent, then their exact `fma` residuals through `log1p` and `expm1`), and for a negative base at an even q the angle by the `real_half_turns` fold, the product in `long double`. A new row field, an exact retry, carries them: the catch in `apply` reads the arm rule first, as today, and calls the row's exact retry where it would have cast to double.

**Tech Stack:** C++20, glibc `pow`, `fma`, `log`, `log1p`, `expm1`, `sinl`, `cosl`, pybind11, pytest.

**Spec:** `docs/superpowers/specs/2026-11-19-fractional-exponent-design.md`

## Global Constraints

- Each part within 1 ulp of the spec's Expected; a part whose Expected is `0` is `+0.0`. The sum row: each part within `1e-14` of its own size.
- Expected values are the spec's, mathematically correct; never today's value.
- Use what exists: `calc_detail::require*` (`calc/internal/helpers.hpp`), `power_retry_arm` and the `with_*` row builders (`ops.hpp`), the fold of `Calculator::real_half_turns` (`trig.cpp`). Nothing is renamed.
- New things, each argued in the spec: the row field `exact_retry` (an `Arm` cannot carry `p/q`), `Calculator::real_power` and `Calculator::principal_power`, the shared chooser `ops::detail::exact_power`, the fold helper `calc_detail::fold_half_turns<T>` (moved out of `real_half_turns`, not copied).
- No branch without a named input that goes wrong without it. The branches this plan has: negative base at an even q to `principal_power` (`(-2)^(1.1)`), odd p negated (`(-2)^(1/9007199254740993)`), `p = 1` with `q` an exact double to `Calculator::root(double, double)` (`109889063671⌄3`), a zero part made `+0` in `principal_power` (`(-4)^(1/2)`), Root's zero degree before `1/y` (`(5)⌄(0)`), Root declining a degree whose reciprocal is past int64 (`(2)⌄(-9223372036854775807-1)`), the catch reading `exact_retry` only on a double retry (`3037000500^2`, `⏨(19)` stay BigReal). No midpoint check, no BigReal fallback.
- An int64 operand is converted to double before any `abs` or negation: `-9223372036854775807-1` has no int64 negation.
- Constants are named `constexpr`, no bare literals (tidy stops the push).
- Values are written in the flat op form; no em dash.
- No commit without the human agent's approval of the diff; `make cpp-format` and `make py-lint-fix` at every commit point. Never run clang-tidy. After every C++ change, `make native-build`.
- The glossary's Retry entry names `retry_arm`; its update goes on the `docs/glossary-additions` branch, not here.

## Review Focus

- A base near 1 at a large exponent (`1000001/1000000` at `10^6`): `log1p` and `expm1`, not a first-order term, keep it within 1 ulp.
- An int64 operand past `2^53`: `9223372036854775807⌄3` stays `2097152`, `(-9223372036854775807-1)⌄(9223372036854775807)` is `-1`, `(-9223372036854775807-1)^(1/2)` is `0 + 3037000499.97605 i`.
- A part on an axis is `+0.0`, never `-0.0` (`(-4)^(1/2)`: the probe's fold gave `-0.0`); `real_half_turns` keeps its results, signed zeros included.
- A whole exponent: decided by `power_retry_arm` alone; `3037000500^2` and `⏨(19)` stay BigReal.
- `Root` at the degree `-9223372036854775807-1`: `1/y` is past int64, the exact retry declines, and #249's `(2)⌄(-9223372036854775807-1)` `1.0` and `(-1)⌄(-9223372036854775807-1)` `1 - 3.4061215800865545e-19 i` stay.

### Task 1: The e2e rows, red first

**Files:**
- Modify: `tests/py/e2e/test_eval_e2e.py`: `RootCase` takes a complex Expected and a `rel`; the new rows go into `ROOT_CASES`; `test_bigreal_exact_results`; `TestRational.test_raises_math_error`.

**Interfaces:**
- Produces: `RootCase` and `test_root_correctly_rounded`.

- [ ] **Step 1: Widen the root table**

```python
@dataclass(frozen=True)
class RootCase:
    expr: str
    expected: float | complex  # each part mpmath rounded to double; a zero part is +0
    ulps: int  # 0 where the kernel is correctly rounded, else 1
    id: str
    rel: float = 0.0  # 0: within ulps; else each part within rel of its own size
```

`test_root_correctly_rounded` checks the type, an exact zero part as `+0`, and every other part within `ulps` of the ulp on got's side of want (`abs(math.nextafter(want, got) - want)`; below a power of two that ulp is half the one above) or within `rel` of its size.

The new rows go into `ROOT_CASES` at 1 ulp: every double and complex row of the spec's three tables with its Expected column, except `(-10)⌄5` and `(-4)⌄2` (existing rows) and the three rows marked not this path. A double Expected is a `float`, a complex one a `complex` (`complex(0.0, -2.8284271247461903)`); a real row's `imag` is `0.0`. The sum row has `rel=1e-14`. Ids say the case (`pow-negative-base-near-one`, `root-fraction-degree-17`, `pow10-twenty-two-sevenths`, `root-parity-past-2-53`, `root-int64-min-odd-degree`).

- [ ] **Step 2: The existing tables**

- `ROOT_CASES`: `109889063671⌄3` is `4789.80858033901` at 0 ulps (`root-integer-degree-correctly-rounded`). Green today; it goes red if a whole degree leaves #271's kernel.
- `test_bigreal_exact_results`: `param("3037000500^2", "9223372037000250000", id="pow-whole-exponent-past-int64-stays-bigreal")` and `param("⏨(19)", "1e19", id="pow10-whole-past-int64-stays-bigreal")`.
- `test_raises_math_error`: `(5)⌄(0)`, `0^(-1/2)`, `0⌄(-2)`.

- [ ] **Step 3: Run and record which rows are red**

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -k "exact_exponent or bigreal_exact or raises_math_error" 2>&1 | tail -40`
Expected: every row whose spec Today is more than 1 ulp off, or has a nonzero zero part, or is a complex where Expected is real, fails; the sum row fails; every other row, the BigReal pins and the error rows pass. A row the spec shows wrong that passes is a finding: stop and report it.

- [ ] **Step 4: Commit point (no commit without approval)**

### Task 2: The two Calculator methods and the fold helper

**Files:**
- Modify: `src/native/lib/calc/internal/helpers.hpp` (the fold helper, beside `half_turn_fold_overflows`)
- Modify: `src/native/lib/calc/trig.cpp:206` (`real_half_turns` reads the helper)
- Modify: `src/native/lib/calc/pub/calculator.hpp` (two declarations beside `Rational pow(const Rational &, const Rational &)`)
- Modify: `src/native/lib/calc/arithmetic.cpp` (the two methods)
- Test: `src/native/tests/unit/test_arithmetic.cpp` (two new tables)

**Interfaces:**
- Produces: `template <class T> struct HalfTurns { T sin; T cos; };` and `template <class T> HalfTurns<T> fold_half_turns(const Rational &t)` in `calc_detail`, for `double` and `long double`, with both the int64 and the int256 fold of today's `real_half_turns`; its signs are today's, so `real_half_turns` does not change.
- Produces: `double Calculator::real_power(const Rational &x, const Rational &y) const` (x > 0, or x < 0 with an odd denominator of y: the sign is `(-1)^p`); `Complex Calculator::principal_power(const Rational &x, const Rational &y) const` (x < 0, even denominator).

- [ ] **Step 1: Write the failing native tests**

Two tables in `test_arithmetic.cpp`, typed structs with designated initializers, run through `test_detail::with_case`, each part checked within 1 ulp (`tol` in ulps, a zero expected part exactly `+0`):
- `RealPowerCase{id, x, y, expected, tol}` (double, `tol` 1 ulp unless named): `17` at `8711/674` is `7993386127887876.0`; `38/3` at `20993/82` is `1.9724528358173784e+282`; `10` at `331897/1242` is `1.6898894438436359e+267`; `1/2` at `8711/674` is `0.00012864363123970833`; `-2` at `1/9007199254740993` is `-1.0`; `-9223372036854775807-1` at `1/9223372036854775807` is `-1.0`; `9223372036854775807` at `1/3` is `2097152.0`; `109889063671` at `1/3` is `4789.80858033901` at 0 ulps; `-10` at `1/5` is `-1.5848931924611134`.
- `PrincipalPowerCase{id, x, y, expected}` (Complex): `-2` at `10000000000001/10000000000000` is `(-2.0000000000001386, -6.283185307180022e-13)`; `-2` at `3/2` is `(0.0, -2.8284271247461903)`; `-1/2` at `3/2` is `(0.0, -0.3535533905932738)`; `-4` at `1/2` is `(0.0, 2.0)`; `-10` at `301/2` is `(0.0, 3.1622776601683793e+150)`; `-3` at `609803/1058` is `(3.8745589136552445e+274, 9.2182330420805e+274)`; `-9223372036854775807-1` at `1/2` is `(0.0, 3037000499.97605)`.

- [ ] **Step 2: Run to see them fail**

Run: `make native-build 2>&1 | tail -5`
Expected: build fails, `real_power` and `principal_power` are not members of `Calculator`.

- [ ] **Step 3: Move the fold into `fold_half_turns<T>`**

`real_half_turns` becomes the call to `fold_half_turns<double>(t)` plus its `switch` on `fn` and the tangent's pole. `make native-build && make native-test 2>&1 | tail -5`: the `real_half_turns ::` rows in `test_trig.cpp` stay green.

- [ ] **Step 4: Implement the methods**

With `a/c = |x|` and `p/q = y`, every operand converted to double first:

```cpp
const double b = a / c, e = p / q, r = std::pow(b, e);
const double t = std::fma(-e, q, p) / q * std::log(b) + e * std::log1p(std::fma(-b, c, a) / c / b);
// real_power: p == 1 and q an exact double: root(signed x as double, q), #271's kernel;
//             else std::fma(r, std::expm1(t), r), negated for x < 0 at an odd p
// principal_power: m = (long double)r + (long double)r * expm1(t); fold_half_turns<long double>(y);
//                  {(double)(m * cos), (double)(m * sin)}, a zero part as +0.0
```

- [ ] **Step 5: Run the native tests**

Run: `make native-build 2>&1 | tail -3 && make native-test 2>&1 | tail -5`
Expected: all pass, the new rows included.

- [ ] **Step 6: Commit point (no commit without approval)**

### Task 3: The exact retry on the rows and in the catch

**Files:**
- Modify: `src/native/lib/parser/pub/ops.hpp`: `ExactRetry` type and `OpRow::exact_retry` after `retry_arm` (933, 957-966); the six positional `OpRow` constructions pass it (974, 978, 982, 987, 991, and `without_rational` at 1019-1027); `with_exact_retry`; `build_exact_retries` and `exact_retry_of` beside `build_retry_arms` (1260-1271); `detail::exact_power`; the `Pow`, `Root` and `Pow10` rows (1085-1104, 1194-1198).
- Modify: `src/native/lib/eval/eval.cpp` (the catch, 448-476).
- Test: `src/native/tests/unit/test_eval.cpp` (`negative_base_apply_cases`, 982).

**Interfaces:**
- Consumes: `Calculator::real_power`, `Calculator::principal_power` (Task 2).
- Produces: `using ExactRetry = std::optional<Value> (*)(const Calculator &, std::span<const Value> args);` (no value: the catch casts to double as today), `constexpr ExactRetry exact_retry_of(OpId)`, `Value detail::exact_power(const Calculator &, const Rational &x, const Rational &y)`.

- [ ] **Step 1: Write the failing apply rows**

In `negative_base_apply_cases` (it compares with `expect_near`, absolute `1e-15`, so only rows it can tell apart): `root :: a degree past 2^53 is odd` (`{OpId::Root, {Rational(-2), Rational(9007199254740993)}}` is `-1.0`, today `1 + 3.487868498008632e-16 i`); `root :: int64 min at an odd degree past 2^53` (`{OpId::Root, {Rational(-9223372036854775807 - 1), Rational(9223372036854775807)}}` is `-1.0`). The ulp line, the `+0` parts and Pow10 (`⏨(331897/1242)`, today 478 ulps off) are proven by Task 1's e2e rows and Task 2's tables, which read them.

- [ ] **Step 2: Run to see them fail**

Run: `make native-build 2>&1 | tail -3 && make native-test 2>&1 | grep -E "FAIL|passed" | tail -10`
Expected: the two rows fail with today's complex values.

- [ ] **Step 3: Implement the rows and the catch**

- `detail::exact_power`: a negative `x` with an even `y.denominator()` is `Value{c.principal_power(x, y)}`, anything else `Value{c.real_power(x, y)}`.
- Rows: `Pow` `exact_power(c, x, y)`; `Root` `std::nullopt` at a numerator of int64 min, else `exact_power(c, x, Rational(y.denominator(), y.numerator()))`; `Pow10` `exact_power(c, Rational(kDecimalBase), a)`.
- The catch: where today it casts every operand to double, it first asks `exact_retry_of(id)`; with one, `result` is its value and the cast, `promote_complex` and the second kernel call are skipped; `promote_range` follows as today and now sees the `Rational` operands. The BigReal arm branch is untouched.

- [ ] **Step 4: The zero degree, red then green**

Add the single case `{OpId::Root, {Rational(5), Rational(0)}}` throws `CalculatorError` (`EXPECT_THROWS`, reason: it must not be `bad_rational`). Run it: it fails with `boost::bad_rational` from `Rational(1, 0)`. Then `Root`'s row raises the zero degree first with `calc_detail::require_nonzero` on its numerator; run again, it passes.

- [ ] **Step 5: Run native and e2e**

Run: `make native-build 2>&1 | tail -3 && make native-test 2>&1 | tail -3 && PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q 2>&1 | tail -5`
Expected: all pass, every Task 1 row included.

- [ ] **Step 6: The #249 edge stays as it is**

Add e2e rows `(2)⌄(-9223372036854775807-1)` `1.0` and `(-1)⌄(-9223372036854775807-1)` `complex(1.0, -3.4061215800865545e-19)` to `EXACT_EXPONENT_CASES` (green on `c85296e`); first run them without the int64 min check and see them raise `bad_rational`, then with it and see them pass.

- [ ] **Step 7: Typecheck and the suites that read the ops table**

The ops table is read everywhere, so this is the case for the whole suite: `make native-test`, `make typecheck`, `make py-test`.
Expected: all green.

- [ ] **Step 8: Commit point (no commit without approval)**

### Task 4: Cost and docs

**Files:**
- Modify: `docs/superpowers/findings/fractional-exponent.md` (the Release cost before and after)
- Modify: `docs/parser.md` or `docs/architecture.md` only where they describe the retry (`grep -n "retry" docs/parser.md docs/architecture.md docs/data-flow.md`)

- [ ] **Step 1: Measure the cost in Release, before and after**

A C++ probe linking `libcalc_core.a` built with `make native-build NATIVE_BUILD_TYPE=Release`: `apply` of `Pow(-2, 11/10)`, `Pow(17, 8711/674)`, `Pow(38/3, 20993/82)`, `Root(12, 2)` and `Root(17, 6)`, 200000 calls each, on `c85296e` (a detached checkout of it) and on the branch. Record both in the findings. More than 5 % slower on any row is a finding: stop and report it. Rebuild with the default type afterwards.

- [ ] **Step 2: Update the docs the grep finds**

Where a doc says a refused fractional power retries in double, it now says the row's exact retry computes it from the exact operands. If the grep finds no such sentence, nothing changes.

- [ ] **Step 3: Format and lint**

Run: `make cpp-format && make py-lint-fix && git diff --stat`

- [ ] **Step 4: Commit point (no commit without approval)**
