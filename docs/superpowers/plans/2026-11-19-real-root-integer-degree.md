# Real Root at an Integer Degree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the double and BigReal `Calculator::root` give the correctly rounded root at an integer degree, and an exact BigReal root is exact (#271).

**Architecture:** the positive-radicand root in both kernels, today `pow(x, 1/y)`, is corrected by Boost's `newton_raphson_iterate` from that `pow` guess when the degree is an integer; in double only when `|ilogb(x)| >= 9`, where `pow` passes 1 ulp. Two `newton_root` overloads go beside the BigComplex one in `transcendental.cpp`'s anonymous namespace. The rest of each kernel (its checks, the reciprocal-degree path, the odd-degree sign) keeps its order.

**Tech Stack:** C++20, Boost.Multiprecision (`cpp_dec_float_50`), pybind11, pytest.

**Spec:** `docs/superpowers/specs/2026-11-19-real-root-integer-degree-design.md`

## Global Constraints

- No header, helper, error kind or op table row changes; nothing is renamed.
- No branch without an input, and each one has a test that goes red without it: the integer degree past the bound (`(1e300)⌄3`), degree 2 to `sqrt` (`(1.7976931348623157e308)⌄2`), the midpoint side (`(7.4762568165974985e-159)⌄(-4)`), `snap_integer` on both BigReal paths (the quotient degree tests), and the Newton value when the 50-digit check fails (`root(2e300, 3)` at tol `1e40`). The BigReal zero radicand (`(1e300*0)⌄3`) needs none.
- 1 ulp is accepted on the double arm; the bound `|ilogb(x)| >= 9` is a named constant (findings `real-root.md`).
- The Newton is Boost's `boost::math::tools::newton_raphson_iterate`; no hand-written Newton step.
- Expected values are the mathematically correct ones from the spec's tables; no today's value. A double row has no tolerance, apart from the accepted 1 ulp of `(-10)⌄5` under the bound.
- Values are written in the flat op form, never LaTeX.
- No commit without the human agent's approval of the diff; `make cpp-format` and `make py-lint-fix` before it. Never run clang-tidy.
- No em dash.

## Review Focus

- A degree past `int` (`2⌄(10^30)`): `as_int` refuses, so it stays on `pow`; it stays `BigReal 1`.
- A negative radicand at an even degree: leaves through the domain rule before the kernel; `(-4)⌄2` stays `complex 2j`.
- A reciprocal degree on a negative radicand: the `whole(1 / y)` path, an integer power, untouched; `(-1e10)⌄(1/3)` stays `-1e+30` (double) and `(-10^400)⌄(1/3)` `-1e+1200` (BigReal).
- A zero radicand at a negative degree: still refused (`require`), `(1e300*0)⌄(-3)` stays a Math Error.
- The irrational BigReal rows: the Newton value is returned when the 50-digit check fails, never the rounded one.

### Task 1: The double root

**Files:**
- Modify: `src/native/lib/calc/transcendental.cpp` (anonymous namespace at the top; `Calculator::root(double, double)` at 45-57)
- Test: `src/native/tests/unit/test_transcendental.cpp` (`real_bin_cases`, line 177)
- Test: `tests/py/e2e/test_eval_e2e.py` (new test after `test_bigreal_exact_results`, line 710)

**Interfaces:**
- Produces: `double newton_root(double x, int n)` in the anonymous namespace.

- [ ] **Step 1: Write the failing native rows**

In `real_bin_cases`, one row per double row of the spec, `.fn = REAL_BIN_FN(root)`, `.tol = 0.0`, ids `"root :: <input>"`. The operands are what the kernel receives: `(1e300, 3) 1e100`, `(-1e300, 3) -1e100`, `(1e-300, 3) 1e-100`, `(1e300, -3) 1e-100`, `(1e100, 7) 193069772888325.03`, `(9223372036854775807.0, 3) 2097152.0`, `(123456789, 9) 7.926057519414248`, `(-10, 5) -1.5848931924611134`, `(2, 3) 1.2599210498948732`, `(3, 3) 1.4422495703074083`, `(10, 3) 2.154434690031884`, `(0.5, 3) 0.7937005259840998`, `(2, 2) 1.4142135623730951`, `(1.5, 2) 1.224744871391589`, `(2, 7) 1.1040895136738123`, `(100, 5) 2.51188643150958`, `(5, 10) 1.174618943088019`, `(2, -3) 0.7937005259840998`, `(2.5, 4) 1.2574334296829355`, `(17, 6) 1.6035216215125492`, `(-2, 3) -1.2599210498948732`. The existing `root :: cube` and `root :: negative at an odd degree` rows move to `tol = 0.0`. `root :: -10 at 5` has `.tol = std::numeric_limits<double>::epsilon()` (one ulp at 1.58, the accepted error under the bound). Add `root :: 2 at int min`: `(2.0, -2147483648.0) 0.9999999996772282`, `tol` 0.

- [ ] **Step 2: Write the failing e2e test**

`@dataclass(frozen=True) class RootCase: expr: str; expected: float; ulps: int`, a `ROOT_CASES` table of the spec's 21 double rows (input as typed there, `ulps` 0, `(-10)⌄5` 1), parametrized with ids from a short `id` field or `pytest.param(..., id=...)`, and:

```python
def test_root_correctly_rounded(case: RootCase) -> None:
    out = _eval(case.expr)
    assert type(out) is float
    assert abs(out - case.expected) <= case.ulps * math.ulp(case.expected)
```

The table head says once why it is not in the golden table (its `pytest.approx` accepts a root several ulps off).

- [ ] **Step 3: Run both and see them red**

Run: `make native-build && make native-test 2>&1 | grep -E "FAIL|passed|failed" | head -20`
Expected: 7 rows fail (`1e300`, `-1e300`, `1e-300`, `1e300 at -3`, `1e100 at 7`, int64 max, `123456789 at 9`); `-10 at 5` and `2 at int min` pass.

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -k test_root_correctly_rounded -q`
Expected: 7 failed, 14 passed.

- [ ] **Step 4: Implement `newton_root(double x, int n) -> double`**

Replace the hand step written earlier. `constexpr int kRootPowWithinUlpExponent = 8;` (why: findings, `pow` stays within 1 ulp up to that `|ilogb|`). `newton_root`: `g = std::pow(x, 1.0 / n)` in `long double`, `boost::math::tools::newton_raphson_iterate(f, g, g / 2, g * 2, std::numeric_limits<long double>::digits, max_iter)` with `f(z) = {p - x, n * p / z}`, `p = power_by_squaring(z, n)`, `max_iter` a named constant; return `static_cast<double>`. In `Calculator::root(double, double)`, both `pow(±x, 1.0 / y)` calls become `newton_root(±x, *n)` when `const auto n = calc_detail::as_int(y)` holds and `std::abs(std::ilogb(x)) > kRootPowWithinUlpExponent`; the `whole(1.0 / y)` path stays.

- [ ] **Step 5: Run both and see them green**

Same commands as Step 3. Expected: all rows pass, `make native-test` reports no failure.

- [ ] **Step 6: Stop for the commit**

Run `make cpp-format && make py-lint-fix`, show the diff, and wait. Proposed message: `fix/calc: double root at an integer degree is correctly rounded`.

### Task 2: The BigReal root

**Files:**
- Modify: `src/native/lib/calc/transcendental.cpp` (anonymous namespace; `Calculator::root(const BigReal &, const BigReal &)` at 130-141)
- Test: `src/native/tests/unit/test_transcendental.cpp` (new `BigBinCase` after `big_cases`, line 311; single cases at 355-367)
- Test: `tests/py/e2e/test_eval_e2e.py` (`test_bigreal_exact_results`)

**Interfaces:**
- Produces: `BigReal newton_root(const BigReal &x, int n)` in the anonymous namespace.

- [ ] **Step 1: Write the failing native rows**

Add `using BigBinFn = BigReal (Calculator::*)(const BigReal &, const BigReal &) const;`, `#define BIG_BIN_FN(name)`, and `struct BigBinCase { const char *id; BigBinFn fn; const char *x; const char *y; const char *expected; const char *tol; };` beside their unary siblings, and a `big_bin_cases` table with a loop shaped like the `big_cases` loop (`nullptr` tol is `EXPECT_EQ`, otherwise `approx_big`). Rows, all `BIG_BIN_FN(root)`: `(-27, 3) -3`, `(8e300, 3) 2e100`, `(-8e300, 3) -2e100`, `(1e300, 3) 1e100`, `(1e400, 4) 1e100`, `(3.2e501, 5) 2e100`, `(1e600, 6) 1e100`, `(1e300, -3) 1e-100`, `(4e200, 2) 2e100`, `(0, 3) 0`, exact; `(2e300, 3) 1.2599210498948731647672106072782283505702514647015e100` tol `1e51`; `(3e400, 7) 1.6256135930564983571755339554548206636303884914531e57` tol `1e8`. Delete the single case `bigreal :: root negative odd degree` (now the `(-27, 3)` row). `bigreal :: root of a negative takes a quotient degree` stays single and asserts `EXPECT_EQ(ctx, c.root(BigReal("-8"), BigReal("9e400") / BigReal("3e400")), BigReal("-2"))`.

- [ ] **Step 2: Write the failing e2e rows**

In `test_bigreal_exact_results`: `(8*10^300)⌄3-2*10^100`, `(-8*10^300)⌄3+2*10^100`, `(10^300)⌄3-10^100`, `(10^400)⌄4-10^100`, `(32*10^500)⌄5-2*10^100`, `(10^600)⌄6-10^100`, `(10^300)⌄(-3)-10^(-100)`, `(4*10^200)⌄2-2*10^100`, each `"0"`; `(2*10^300)⌄3` `"1.259921049894873e+100"`; `(3*10^400)⌄7` `"1.625613593056498e+57"`; `(1e300*0)⌄3` `"0"`.

- [ ] **Step 3: Run both and see them red**

Run: `make native-build && make native-test 2>&1 | grep -E "FAIL|passed|failed" | head -20`
Expected: the exact rows and the quotient case fail; record whether the two irrational rows fail (the spec allows either); `(0, 3)` passes.

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -k test_bigreal_exact_results -q`
Expected: the 8 new `0` rows fail; the irrational and zero rows pass.

- [ ] **Step 4: Implement `newton_root(const BigReal &x, int n) -> BigReal`**

`g = pow(x, BigReal(1) / n)`; `newton_raphson_iterate(f, g, BigReal(0), BigReal(g * 2), std::numeric_limits<BigReal>::digits, max_iter)` with `f(z) = {p - x, n * p / z}`, `p = pow(z, n)` (Boost's integer `pow`); `const BigReal z50(z.str(kBigRealPrecisionDigits))`; return `z50` when `pow(z50, n) == x`, else `z`. In `Calculator::root(const BigReal &, const BigReal &)`, both `pow(±x, BigReal(1) / y)` calls become `newton_root(±x, *n)` when `const auto n = calc_detail::as_int(calc_detail::snap_integer(y))` holds; the `whole(m)` path stays.

- [ ] **Step 5: Check the zero radicand on the Newton path**

With no zero branch, the `(0, 3)` row and `(1e300*0)⌄3` stay `0`: Boost returns the guess when `f` is `0`. (A zero branch was tried and removed; findings `real-root.md`.)

- [ ] **Step 6: Run both and see them green**

Same commands as Step 3, then `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q`. Expected: all pass; `make native-test` reports no failure.

- [ ] **Step 7: Check the Review Focus inputs e2e**

Run the probe `e2e_any.py` on `2⌄(10^30)`, `(-4)⌄2`, `(-1e10)⌄(1/3)`, `(-10^400)⌄(1/3)`, `(1e300*0)⌄(-3)`. Expected: the values in Review Focus, measured on this branch before the fix (2026-11-19).

- [ ] **Step 8: Stop for the commit**

Run `make cpp-format && make py-lint-fix`, show the diff, and wait. Proposed message: `fix/calc: BigReal root at an integer degree, exact when the root is`. The spec, the plan and the findings go in a `docs/superpowers` commit, shown with it.

### Task 3: Review fixes (added after the whole-branch review)

**Files:** `src/native/lib/calc/transcendental.cpp`, `src/native/tests/unit/test_transcendental.cpp`, `tests/py/e2e/test_eval_e2e.py`, findings `real-root.md`.

- [ ] **Step 1: Failing rows.** Add the spec's review rows to `real_bin_cases` (tol 0) and `ROOT_CASES` (ulps 0); add `bigreal :: root of a positive takes a quotient degree` and the e2e row `(8*10^300)⌄(9*10^400/(3*10^400))-2*10^100` `"0"`.
- [ ] **Step 2: Red.** `make native-test`: the 6 double rows fail. Removing `snap_integer` on the BigReal positive path turns the quotient tests red; put it back.
- [ ] **Step 3: Fix.** In `Calculator::root(double, double)`, `n == 2` returns `this->sqrt(x)`; in `newton_root(double, int)`, a `long double` result on a double midpoint takes the side from the sign of `f(z).first`.
- [ ] **Step 4: Green, and each branch needed.** All rows pass; dropping the `sqrt` branch turns the two degree 2 rows red.
- [ ] **Step 5: Stop for the commit.**
