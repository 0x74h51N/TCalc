# BigReal Domain and Power Roots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A negative BigReal under sqrt, root, ln and log becomes a BigComplex; a negative base under a root's exponent is that root; complex powers lose the `exp(log)` noise; the BigComplex root keeps a degree past the double range.

**Architecture:** The domain rule of each op row is stored for double and for BigReal, and `promote_complex` reads the one that matches the arm `coerce` left. Pow gets Root's rule read on `1 / b`. The real pow kernels hand a root's exponent to `Calculator::root`; the complex pow kernels reuse root's exact integer power and hand a root's exponent to root.

**Tech Stack:** C++20, Boost.Multiprecision (`cpp_dec_float_50`, `cpp_complex_50`), pybind11, pytest.

**Spec:** `docs/superpowers/specs/2026-11-11-bigreal-domain-design.md`. Findings: `docs/superpowers/findings/bigreal-domain.md`.

## Global Constraints

- No em dash anywhere. Everything in the repository is in English.
- Test rows are written before the fix and are never changed to match the code. Expected values are the exact value rounded to the type (mpmath, at least 60 digits).
- No commit without the human agent's approval of its diff; each commit step stops there. Stage files by name. Never `--no-verify`.
- Never run clang-tidy. `make cpp-format` and `make py-lint-fix` before each commit.
- Run `make native-build` after every C++ change. Run only the tests named in the task.
- Native test rows: typed struct, designated initializers, one table and one loop per signature, the function a field of the row, `tol` `nullptr` means exact.

## Review Focus

- `(-2)^{2/3}` becomes the principal complex root while `(-8)^{2/3}` stays the real `4`: the spec's stated gap; the reviewer checks no row claims otherwise.
- A Root or Pow degree that is an integer at 50 digits but not in the guard digits (`9e400/3e400`): `odd_integer(BigReal)` must snap, as `Calculator::root(BigReal)` does today; the existing native row at `test_transcendental.cpp:351` covers it.
- A zero base or radicand on the complex arms (`(0+0i)^{0.5}`, `(0+0i)⌄3`): must end, not recurse; the Task 3 row `pow :: zero base, half` and the existing `zero radicand, degree 3` cover it.
- Log with a BigReal base and argument (`log_{2}(-10^{400})`): the default base and the argument are both BigReal after `coerce`; the promotion lifts the argument and the second `coerce` lifts the base; Task 4 step 1 adds its row.

### Task 1: One odd-integer test for the root kernels and Root's rule

A pure move: no behavior changes, so no new test; the existing suite staying green is the check.

**Files:**
- Modify: `src/native/lib/calc/internal/helpers.hpp` (add `whole`, `odd_integer`)
- Modify: `src/native/lib/calc/transcendental.cpp:56-70` (`Calculator::root(double)`), `:145-165` (`Calculator::root(BigReal)`)
- Modify: `src/native/lib/parser/pub/ops.hpp:886` (`kDomainEpsilon` goes), `:992-999` (`power_needs_big`), `:1013-1020` (Root's rule)

**Interfaces:**
- Produces: `bool calc_detail::whole(double y)` (`floor(y) == y`, what `std::pow` asks) and `bool calc_detail::whole(const BigReal &y)` (`snap_integer`, then `floor` equality, the lines now in `Calculator::root(BigReal)`); `bool calc_detail::odd_integer(double y)` (`int_like(y)` and the rounded value is odd) and `bool calc_detail::odd_integer(const BigReal &y)` (`whole(y)` and `fmod(snapped, 2) != 0`).

- [ ] **Step 1: Baseline.** Run `make native-build && make native-test` and `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -p no:randomly`. Expected: native all pass; e2e has exactly the 12 known red rows of section "a BigReal outside the real domain". Write both counts in the ledger.
- [ ] **Step 2: Add `whole` and `odd_integer`** to `calc/internal/helpers.hpp`, after `snap_integer`. Both root kernels call it in place of their own lines: in `Calculator::root(double)` the two `require` calls raise the same Math error, so `require(odd_integer(y))` replaces both.
- [ ] **Step 3: Root's rule and `power_needs_big`** read `calc_detail::odd_integer` and `calc_detail::int_like`; `ops.hpp` includes `calc/internal/helpers.hpp`; `detail::kDomainEpsilon` is deleted. `grep -rn kDomainEpsilon src/` prints nothing.
- [ ] **Step 4: Verify.** `make native-build && make native-test`, then the e2e file as in step 1. Expected: the same counts as step 1.
- [ ] **Step 5: Commit** after approval: `refactor/calc: one odd-integer test for root and its domain rule`.

### Task 2: The BigComplex root reads `1 / y` in BigReal

**Files:**
- Modify: `src/native/lib/calc/transcendental.cpp:221-239` and its unnamed namespace (`as_int`)
- Test: `src/native/tests/unit/test_transcendental.cpp` (`BigComplexRootCase`, `big_complex_root_cases`, its loop)

**Interfaces:**
- Produces: `template <class T> std::optional<int> as_int(const T &v)` in the unnamed namespace of `transcendental.cpp`, replacing the double-only one: nullopt unless `v` equals its `floor` and fits `int`. Ruling during execution: a BigComplex part is `cpp_bin_float_50`, not BigReal (`cpp_dec_float_50`), so `snap_integer` does not apply; the part is read exactly in its own type, as the double was.

- [ ] **Step 1: Give the BigComplex table `fn` and `tol`**, as `BigCase` has them: `fn` defaults to `Calculator::root` cast to the BigComplex overload, `tol` defaults to `nullptr` (exact); the loop calls `(c.*tc.fn)(tc.x, tc.y)` and compares each part with `approx_big` when `tol` is set. Existing rows keep their values; their ids get the prefix `root :: ` and the loop label becomes `bigcomplex :: `.
- [ ] **Step 2: The failing row.** `{.id = "root :: degree past the double range", .x = BC(-8, 0), .y = BC("1e400"), .expected = BC("1", "3.1415926535897932384626433832795028841971693993751e-400"), .tol = "1e-449"}`.
- [ ] **Step 3: Run it.** `make native-build && make native-test`. Expected: FAIL on that row only (imaginary part `0`).
- [ ] **Step 4: Fix.** `transcendental.cpp:226` reads `as_int(BigComplex::value_type(1) / y.real())` in the part's own type, and line 231 reads `as_int(y.real())` the same way; no `static_cast<double>` is left in `Calculator::root(BigComplex)`.
- [ ] **Step 5: Verify.** `make native-build && make native-test`. Expected: all pass.
- [ ] **Step 6: Commit** after approval: `fix/calc: keep a bigcomplex root degree past the double range`.

### Task 3: Complex powers take root's exact steps

**Files:**
- Modify: `src/native/lib/calc/transcendental.cpp` (`Calculator::root(Complex)` `:173-192`, `Calculator::root(BigComplex)`, the unnamed namespace)
- Modify: `src/native/lib/calc/arithmetic.cpp:219-235` (`Calculator::pow(Complex)`, `Calculator::pow(BigComplex)`)
- Test: `src/native/tests/unit/test_transcendental.cpp` (`ComplexRootCase` and `BigComplexRootCase` tables)

**Interfaces:**
- Consumes: the templated `as_int` from Task 2.
- Produces: per arm, the integer power root runs today, as one function each: `std::optional<Complex> integer_power(Complex x, int m)` (positive `m`: `std::pow(x, m)` when both parts are finite; negative `m` and `x != 0`: the BigComplex run, cast back) and `std::optional<BigComplex> integer_power(const BigComplex &x, int m)` (Boost `pow(x, m)` when finite). They are `calc_detail` inline functions in `calc/internal/helpers.hpp`, which `arithmetic.cpp` and `transcendental.cpp` both include; the root kernels call them in place of their current lines, keeping today's fall-through order (a non-finite positive power falls to the steps after it).

- [ ] **Step 1: Give the Complex table `fn`**, as in Task 2 step 1 (defaults to `Calculator::root`, ids get `root :: `, label `complex :: `).
- [ ] **Step 2: The failing rows**, `.fn` set to `Calculator::pow` cast to the overload:
  - Complex: `pow :: negative, half` `(-4,0)^(0.5,0)` = `(0,2)`; `pow :: huge negative, half` `(-1e20,0)^(0.5,0)` = `(0,1e10)`; `pow :: negative, minus half` `(-4,0)^(-0.5,0)` = `(0,-0.5)`; `pow :: gaussian square` `(3,4)^(2,0)` = `(-7,24)`; `pow :: one plus i squared` `(1,1)^(2,0)` = `(0,2)`; `pow :: gaussian, minus two` `(3,4)^(-2,0)` = `(-0.0112,-0.0384)`; `pow :: zero base, half` `(0,0)^(0.5,0)` = `(0,0)`.
  - BigComplex: `pow :: huge negative, half` `("-4e400","0")^BC("0.5")` = `("0","2e200")`; `pow :: gaussian square` `(3,4)^BC(2)` = `(-7,24)`; `pow :: negative, quarter` `(-4,0)^BC("0.25")` = `(1,1)`.
- [ ] **Step 3: Run them.** `make native-build && make native-test`. Expected: the noisy rows FAIL; write in the ledger which rows already pass (a guard that passes before the fix proves nothing and is named as a guard).
- [ ] **Step 4: Extract `integer_power`** from the two root kernels; the root rows stay green.
- [ ] **Step 5: Pow on both complex arms**, for an exponent with zero imaginary part: `as_int(b)` gives `m` and `integer_power(x, m)` has a value: return it; `as_int(1 / b)` gives `n` and `x != 0`: return `this->root(x, n)`; otherwise the library `pow` as today.
- [ ] **Step 6: Verify.** `make native-build && make native-test`; `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -p no:randomly`. Expected: native all pass; e2e the same 12 known red rows and nothing else.
- [ ] **Step 7: Commit** after approval: `fix/calc: complex powers use the exact root steps`.

### Task 4: The domain rule reads a BigReal in its own type

**Files:**
- Modify: `src/native/lib/parser/pub/ops.hpp` (`DomainRule`, `OpRow`, `with_domain`, `build_domains`, `domain_of`, the rule lambdas)
- Modify: `src/native/lib/eval/eval.cpp:184-212` (`promote_complex`)
- Modify: `src/native/lib/calc/transcendental.cpp:127-129` (the comment of `Calculator::log(BigReal, BigReal)` that says a BigReal is never domain-checked)
- Test: `src/native/tests/unit/test_eval.cpp:318-324`; `tests/py/e2e/test_eval_e2e.py` (the 15 rows already on the branch)

**Interfaces:**
- Consumes: `calc_detail::odd_integer` from Task 1.
- Produces: `struct DomainRule { bool (*on_double)(double, double); bool (*on_big)(BigReal, BigReal); }` and `template <class F> constexpr DomainRule domain_rule(F f)` that fills both from one capture-less generic lambda whose parameters are taken by value (the form the scratch probe compiled). `domain_of(id)` returns it; an op with no rule has both pointers null.

- [ ] **Step 1: Replace the pinning test.** `domain :: a BigReal argument is never domain-checked` becomes two rows in the style of the domain tests above it: `promote_complex(OpId::Sqrt, {BigReal("-1")})` leaves `Arm::BigCx`; `promote_complex(OpId::Ln, {BigReal("1e-400")})` leaves `Arm::Big`. In the e2e golden section "a BigReal outside the real domain" add `log_{2}(-10^{400})` BigComplex `"1328.771237954945+4.532360141827194i"`.
- [ ] **Step 2: Run.** `make native-build && make native-test`. Expected: the first row FAILS, the second passes (it is the guard the old test named); the new e2e row fails with Math error.
- [ ] **Step 3: Implement.** Rule lambdas become `[](auto x, auto y)`, and a rule that takes an absolute value writes `using std::abs; abs(x)` so BigReal finds Boost's; `with_domain` takes the lambda through `domain_rule`. `promote_complex` drops its BigReal early return; on `Arm::Big` it calls `on_big` with the operands as BigReal (a missing second operand is `BigReal(0)`, as the double side passes `0.0`) and sets `args[0] = lift_to_big_complex(args[0])`; on Int64 or Double it does what it does today. The `log(BigReal)` comment loses the sentence the change makes false.
- [ ] **Step 4: Verify.** `make native-build && make native-test`; `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -p no:randomly`. Expected: native all pass; e2e all pass, the 12 red rows included.
- [ ] **Step 5: Commit** after approval: `fix/eval: a negative bigreal leaves the real domain into bigcomplex`.

### Task 5: A BigReal power snaps its exponent

**Files:**
- Modify: `src/native/lib/calc/arithmetic.cpp:90-94` (`Calculator::pow(BigReal, BigReal)`)
- Test: `tests/py/e2e/test_eval_e2e.py`, `test_bigreal_exact_results` (the table for guard-digit residues)

**Interfaces:**
- Consumes: `calc_detail::snap_integer` (exists).

- [ ] **Step 1: The failing rows** in `test_bigreal_exact_results`: `param("(-8)^{9e400/3e400}", "-512", id="pow-negative-base-exact-quotient-exponent")` and `param("(-8)^{(1e400/3)*3/1e400}", "-8", id="pow-negative-base-exact-product-exponent")`.
- [ ] **Step 2: Run.** `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -p no:randomly -k pow-negative-base`. Expected: both FAIL (`nan`).
- [ ] **Step 3: Fix.** The return line becomes `return pow(a, calc_detail::snap_integer(b));` with a one-line comment on why (the quotient sits under its integer in the guard digits, where Boost reads it).
- [ ] **Step 4: Verify.** `make native-build && make native-test`; the e2e file. Expected: all pass.
- [ ] **Step 5: Commit** after approval: `fix/calc: a bigreal power snaps its exponent`.

### Task 6: A power with a root's exponent is that root

**Files:**
- Modify: `src/native/lib/parser/pub/ops.hpp` (Pow row gets a rule; Root's rule body shared with it)
- Modify: `src/native/lib/calc/arithmetic.cpp:53-56` (`Calculator::pow(double, double)`), `:90-94` (`Calculator::pow(BigReal, BigReal)`)
- Test: `tests/py/e2e/test_eval_e2e.py`, golden table, a new section "a negative base under a root's exponent"

**Interfaces:**
- Consumes: `whole` and `odd_integer` (Task 1), complex pow steps (Task 3), `domain_rule` (Task 4), the snapped BigReal exponent (Task 5).
- Produces: one rule function `leaves_real_root(x, degree)` (today's Root rule body) that Root's row calls with `y` and Pow's row calls with `1 / y` after its `whole` test.

- [ ] **Step 1: The failing rows**, `(expr, type, value)` as the table documents:
  - `(-4)^{0.5}` complex `(0.0, 2.0)`; `(-4)^{-0.5}` complex `(0.0, -0.5)`; `(-8)^{0.25}` complex `(1.189207115002721, 1.189207115002721)`; `(-2)^{1/3}` float `-1.2599210498948732`; `(-2)^{0.3333333333333333}` float `-1.2599210498948732`; `(-2)^{2/3}` complex `(-0.7937005259840998, 1.3747296369986026)`; `(-10^{400})^{0.5}` BigComplex `"0+1e+200i"`; `(-4+0i)^{0.5}` complex `(0.0, 2.0)`.
  - Guards: `(-8)^{1/3}` Rational `"-2"`; `(-8)^{2}` Rational `"64"`.
- [ ] **Step 2: Run.** `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -p no:randomly`. Expected: every non-guard row FAILS (nan or a type mismatch); `(-4+0i)^{0.5}` passes after Task 3 and is named a guard in the ledger.
- [ ] **Step 3: Pow's rule.** `ops.hpp`: Root's rule body becomes `leaves_real_root`; the Pow row adds `with_domain` with `x < 0 && !whole(y) && leaves_real_root(x, 1 / y)`.
- [ ] **Step 4: The real pow kernels.** In `Calculator::pow(double, double)` and `Calculator::pow(BigReal, BigReal)`: a negative base, `!whole(b)`, and `odd_integer(1 / b)`: `return this->root(a, round(1 / b))`. Everything else is unchanged.
- [ ] **Step 5: Verify.** `make native-build && make native-test`; the e2e file. Expected: all pass. Then run `make py-test` once, since the ops table changed (tests rule: a change every area reads).
- [ ] **Step 6: Run the app** (`python -m tcalc`) and type `(-4)^{0.5}`, `(-2)^{1/3}`, `sqrt(-1e400)`, `(3+4i)^{2}`; write what each shows in the ledger.
- [ ] **Step 7: Commit** after approval: `fix/calc: a negative base under a root's exponent is that root`.
