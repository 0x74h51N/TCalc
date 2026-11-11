# Exact Complex Roots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Calculator::root` on the Complex and BigComplex arms returns the correctly rounded principal root wherever the degree allows it (#223, #225).

**Architecture:** Each complex `root` takes the first step that fits the degree: `sqrt` at 2, an integer `pow` when `1 / y` is an integer, the BigComplex arm at any other `int` degree with a nonzero radicand, and today's `pow` otherwise. The BigComplex arm runs Newton for a positive degree and takes `1 / root(x, -y)` for a negative one. Newton is one function in `transcendental.cpp`, called only by the BigComplex `root`.

**Tech Stack:** C++ native core, `std::complex<double>`, Boost `cpp_complex_50`, `boost::math::tools::complex_newton`, the native test framework.

**Spec:** `docs/superpowers/specs/2026-11-10-complex-root-exact-design.md`

## Global Constraints

- Branch `fix/complex-root-noise`. No commit without the human agent's approval of the diff; never `--no-verify`; stage files by name. Never run clang-tidy.
- The rows of `complex_root_cases` and `big_complex_root_cases` are not edited to match the code. The one exception is the `1e30` row, set to `3.1415926535897927e-30` by the human agent's ruling.
- Newton runs only at step 3; a degree that fits steps 1 or 2 never reaches it.
- No e2e row. No em dash.

## Review Focus

- A BigComplex result whose zero part comes back as `-0` (`(-4) ⌄ -2` gave `-0-0.5i` from Newton): checked 2026-11-11, `format_result(BigComplex("-0", "-0.5"))` is `0-0.5i`, the same as for `+0`, so no sign fix is needed. The test compares `-0 == 0` as equal.
- A degree with an imaginary part (`(-4) ⌄ (2+i)`): every step reads `y.real()` only after checking `y.imag() == 0`; it must reach step 4.
- A zero radicand (`\root{0i}{3}`): Newton returns NaN there (zero derivative), so x = 0 takes step 4; rows `zero radicand, degree 3` in both tables.
- Degree 0: `1 / y` is infinite and `require_nonzero(y)` already raises before step 1; the steps must stay after that guard.
- A degree past `int` (`1e30`, `-1e30`): step 4, no cast of an out-of-range double to `int`.
- Degree 1 and -1: step 2 (`pow(x, 1)`, `pow(x, -1)`), exact `x` and `1 / x`, never Newton.

## Task 1: Test rows and the 1e30 ruling

**Files:**
- Test: `src/native/tests/unit/test_transcendental.cpp` (`complex_root_cases`, `big_complex_root_cases`, already written in the tree)

- [ ] **Step 1: Set the `minus one, degree 1e30` row**

`.expected = Z(1.0, 3.1415926535897927e-30)`, with one comment line: `// One ulp from the correctly rounded value: 1/1e30 is not exact in double. Accepted by the human agent, 2026-11-11.`

Add the review rows, expected values from mpmath at 400 bits: Complex `huge negative, degree -2` (`-1e300` → `Z(0.0, -1e-150)`), `tiny negative, degree -2` (`-1e-300` → `Z(0.0, -1e150)`), `minus one, degree -3` (→ `Z(0.5, -0.8660254037844386)`), `negative, degree -3` (`-8` → `Z(0.25, -0.4330127018922193)`), `gaussian, degree -3` (`-117+44i` → `Z(0.12, -0.16)`), `minus one, degree -4` (→ `Z(0.7071067811865476, -0.7071067811865476)`), `zero radicand, degree 3` (`0` → `Z(0.0, 0.0)`); BigComplex `zero radicand, degree 3` (`BC(0, 0)` → `BC(0, 0)`).

- [ ] **Step 2: Build and record the red rows**

Run: `make native-build && make native-test 2>&1 | grep FAILED`
Expected: every `root ::` row fails except `no exact root, degree 3`, `minus one, degree 5`, `gaussian fifth power`, `minus one, degree 1000`, `minus one, degree 1e30` (Complex) and `positive real, degree 3` (BigComplex).

## Task 2: The steps in both `root` overloads

**Files:**
- Modify: `src/native/lib/calc/transcendental.cpp` (unnamed namespace at the top; `Calculator::root(Complex, Complex)`; `Calculator::root(const BigComplex &, const BigComplex &)`)

**Interfaces:**
- Produces: `BigComplex newton_root(const BigComplex &x, int n)` and `std::optional<int> as_int(double)` in the unnamed namespace.

- [ ] **Step 1: Write `newton_root` and `as_int`**

`newton_root`: guess `boost::multiprecision::pow(x, BigComplex(1) / BigComplex(n))`, then `boost::math::tools::complex_newton` on a lambda that returns `{p * z - x, BigComplex(n) * p}` with `p = pow(z, n - 1)`. Include `<boost/math/tools/roots.hpp>`. `as_int`: the value when it is integral and within `int`, else nothing.

- [ ] **Step 2: The steps in `root(Complex x, Complex y)`**

After `require_nonzero(y)`, in this order, steps 1 to 3 only when `y.imag() == 0`:
1. `y.real() == 2`: `return this->sqrt(x);`
2. `as_int(1.0 / y.real())` has m: `return std::pow(x, *m);`
3. `as_int(y.real())` has a value and `x != 0`: `const BigComplex r = this->root(BigComplex(x.real(), x.imag()), BigComplex(y.real()));`, returned as `Complex(static_cast<double>(r.real()), static_cast<double>(r.imag()))`. One comment line: Newton in double leaves an irrational part one ulp off.
4. `return this->pow(x, 1.0 / y);`

- [ ] **Step 3: The same steps in `root(const BigComplex &x, const BigComplex &y)`**

Steps 1, 2 and 4 the same with `BigComplex` (`boost::multiprecision::pow(x, *m)` at step 2); `as_int` reads `static_cast<double>(y.real())`. Step 3, `x != 0` and n from `as_int`: a negative n returns `BigComplex(1) / this->root(x, BigComplex(-n))`, with one comment line naming `(-1e300) ⌄ -2` (Newton's absolute tolerance below 1); a positive n returns `newton_root(x, n)`.

- [ ] **Step 4: Run the native suite**

Run: `make native-build && make native-test 2>&1 | tail -3`
Expected: all pass.

- [ ] **Step 5: Run the e2e evaluation file**

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q 2>&1 | tail -2`
Expected: all pass.

- [ ] **Step 6: Check the screen**

Through `evaluate_branch` and `format_result`: `\root{-1e20}{}` is `10000000000i`, `\root{-117+44i}{3}` is `3+4i`, `\root{-1}{4}` is `0.7071067811865476+0.7071067811865476i`, `\root{-4}{}*10^{17}` is `2e17 i` (formatter's form), `\root{-4*10^{400}+0i}{}/10^{200}` is `2i` with no `e-51` part.

- [ ] **Step 7: Format and stop for review**

Run `make cpp-format`, then show the human agent the diff of `transcendental.cpp`, `test_transcendental.cpp`, the spec, this plan and `docs/superpowers/findings/`. Commit only on approval, staging by name: `fix/calc: exact complex root through sqrt, integer pow and newton`.
