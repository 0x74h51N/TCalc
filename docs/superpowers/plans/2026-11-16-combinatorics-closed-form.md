# nPr and nCr Closed Form Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `permute` and `choose` compute in one Boost call at every size, so `nPr(9223372036854775807,9223372036854775807)` no longer freezes the app (#248).

**Architecture:** The two loops in `src/native/lib/calc/combinatorics.cpp` are replaced by `boost::math::tgamma_delta_ratio` (nPr) and `boost::math::beta` (nCr), in BigReal, rounded to the nearest integer. A result past BigReal's range is `inf`. Nothing outside the two kernels changes except their tests and the two #248 smoke pins.

**Tech Stack:** C++20, Boost.Math 1.83 special functions over `cpp_dec_float<50>`, the native test harness (`test_detail::with_case`), pytest smoke.

**Spec:** `docs/superpowers/specs/2026-11-16-combinatorics-closed-form-design.md`

## Global Constraints

- nPr: `round(tgamma_delta_ratio(BigReal(a) + 1, -BigReal(b), policy))`; nCr: with `k = min(b, a - b)`, `k == 0` is 1, else `BigReal(round(1 / (WideReal(k) * beta(WideReal(k), WideReal(a - k) + 1))))` with `calc_detail::WideReal` (twice BigReal's digits, 64-bit exponent) in `calc/internal/helpers.hpp`.
- The overflow policy `boost::math::policies::policy<boost::math::policies::overflow_error<boost::math::policies::ignore_error>>` is the alias `calc_detail::InfOnOverflow` in `calc/internal/helpers.hpp`, passed to the `tgamma_delta_ratio` call only.
- `nonneg_or_zero(a, b)` stays first in both kernels: a negative operand is the math error, $b > a$ is 0.
- Signatures, ops table rows and coerce rules do not change. The flow around the kernels stays as it is: `int_binary` gives both ops the Int64 arm only, coerce passes int64 operands or reports `integers_only`, and the BigReal result goes back unchanged (`widen_escaped` reads only a double result, and no rule downcasts a result). No code outside `combinatorics.cpp` is touched.
- No bare numeric literal in `src/native/lib` other than 0 and 1 (tidy `avoid-magic-numbers`).
- No em dash anywhere. Commits only after the human agent has seen the diff and approved it. The docs (spec, this plan, findings, findings README) are committed last, in one commit.

## Review Focus

- `nCr(a,a)`: `k == 0`, where `beta(0, ...)` would be a pole, so the kernel's own `k == 0` branch answers 1. Row below.
- Large `a` with small `b` (`nPr(1000000000000000000,3)`) stays exact; that is where `tgamma_delta_ratio` takes its short product. Row below.
- `nPr(a,a)` for `a` past BigReal's range (`9223372036854775807`) is `inf`, not an exception. Row below.
- The Python path (`nPr(5,2)`, `nCr(5,2)` in `tests/py/e2e/test_reductions_e2e.py`) keeps its exact `20` and `10`. Task 1, step 6.

### Task 1: The closed form in both kernels

**Files:**
- Modify: `src/native/lib/calc/combinatorics.cpp` (`permute`, `choose`, the `beta.hpp` include)
- Modify: `src/native/lib/calc/internal/helpers.hpp` (the aliases `InfOnOverflow` and `WideReal`)
- Test: `src/native/tests/unit/test_combinatorics.cpp` (the six `permute` / `choose` cases at the end of `unit_combinatorics`)

**Interfaces:**
- Consumes: `Calculator::permute(long long, long long) const -> BigReal`, `Calculator::choose(long long, long long) const -> BigReal`, `calc_detail::nonneg_or_zero`.
- Produces: the same two signatures, nothing new.

- [ ] **Step 1: Replace the six cases with one typed table**

In the shape of `BigCase` in `test_transcendental.cpp`: `using CombFn = BigReal (Calculator::*)(long long, long long) const;` and

```cpp
/// a and b, then the expected value as text. A null tol asserts exact equality; a tol is relative.
struct CombCase {
    const char *id;
    CombFn fn;
    long long a;
    long long b;
    const char *expected;
    const char *tol;
};
```

One vector, one `for` with `test_detail::with_case(ctx, tc.id, ...)`: a null `tol` asserts `EXPECT_EQ(ctx, got, BigReal(tc.expected))` (`"inf"` included), as `BigCase` in `test_transcendental.cpp` does, otherwise the existing absolute `approx_big(got, want, BigReal(tc.tol) * abs(want))`. Not the templated "scaled" `approx_big`: its `cpp_bin_float_50` tolerance does not mix with BigReal, and a `BigReal` call resolves to the absolute overload anyway. Rows (`MAX` is `std::numeric_limits<long long>::max()`):

| id | fn | a | b | expected | tol |
|---|---|---|---|---|---|
| permute :: basic | permute | 5 | 2 | 20 | null |
| choose :: basic | choose | 5 | 2 | 10 | null |
| permute :: out of range | permute | 5 | 6 | 0 | null |
| choose :: out of range | choose | 5 | 6 | 0 | null |
| choose :: all | choose | MAX | MAX | 1 | null |
| permute :: full 30 | permute | 30 | 30 | 265252859812191058636308480000000 | null |
| permute :: large a small b | permute | 1000000000000000000 | 3 | 999999999999999997000000000000000002000000000000000000 | null |
| choose :: exact mid | choose | 60 | 30 | 118264581564861424 | null |
| choose :: exact 100 | choose | 100 | 50 | 100891344545564193334812497256 | null |
| choose :: exact 48 digits | choose | 176 | 60 | 700938637298704280812242467451564851471559064800 | null |
| permute :: million | permute | 1000000 | 1000000 | 8.2639316883312400623766461031726662911353479789639e+5565708 | 1e-45 |
| choose :: million | choose | 1000000 | 500000 | 7.8995787722769708417702379031791126849833959830511e+301026 | 1e-45 |
| permute :: past BigReal range | permute | MAX | MAX | inf | null |
| choose :: past BigReal range | choose | MAX | 4611686018427387903 | inf | null |

The two `domain throws` cases stay single `TEST_CASE`s, as they are. The million rows are from a `cpp_dec_float_100` loop (findings, `combinatorics.md`).

- [ ] **Step 2: Run, see the red**

Run: `make native-build && make native-test 2>&1 | tail -30`
The two `past BigReal range` rows are left out of this run: on today's loop they never return and hang the whole native run (`subagents.md`: the red phase can hang). They go in at step 3. Expected: `choose :: exact mid` and `choose :: exact 100` fail (today's loop leaves noise in the guard digits, so `==` is false); the other rows pass, the `million` rows included (the loop is accurate there, only slow). Record which rows failed. The red for the freeze itself is the smoke pin in Task 2.

- [ ] **Step 3: Implement**

Add the two `past BigReal range` rows to the table. In `combinatorics.cpp`: add `#include <boost/math/special_functions/beta.hpp>`, the policy alias `calc_detail::InfOnOverflow` in `calc/internal/helpers.hpp` (`code.md`: helpers of a layer go there) with a one-line why (Boost throws `std::overflow_error` by default; past BigReal's range the result is `inf`, as `Γ` shows), and replace the two loop bodies with the calls in Global Constraints. `permute` and `choose` keep `nonneg_or_zero` first.

- [ ] **Step 4: Run, see green**

Run: `make native-build && make native-test 2>&1 | tail -30`
Expected: every `permute ::` and `choose ::` row passes. The smoke pin check now fails on `nPr :: i64 MAX, i64 MAX` (the pinned case passes); that is Task 2's red.

- [ ] **Step 5: Grep the added native lines for numeric literals**

Run: `git diff -U0 src/native/lib | grep '^+' | grep -nE '[0-9]' | grep -v constexpr`
Expected: only `1` and the include line.

- [ ] **Step 6: Python path**

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_reductions_e2e.py -q`
Expected: all pass.

### Task 2: Remove the #248 pins

**Files:**
- Modify: `src/native/tests/smoke/smoke_stress.cpp:52` (the `nPr :: i64 MAX, i64 MAX` row of `kSmokePins`)
- Modify: `tests/py/smoke/test_smoke.py:49` (the `nPr(9223372036854775807,9223372036854775807)` entry of `SMOKE_PINS`)

**Interfaces:**
- Consumes: Task 1's kernels.
- Produces: nothing.

- [ ] **Step 1: See both pins red**

Run: `make native-test 2>&1 | grep -E "pins|nPr :: i64 MAX, i64 MAX"` and `PYTHONPATH=src python -m pytest tests/py/smoke -q -k "nPr" 2>&1 | tail -5`
Expected: the native pin check names the #248 case as passing; pytest reports `XPASS(strict)` for it.

- [ ] **Step 2: Delete the two pin rows**

- [ ] **Step 3: Run both smoke runs**

Run: `make native-test 2>&1 | tail -5` and `make py-smoke 2>&1 | tail -5`
Expected: both green, no #248 failure.

- [ ] **Step 4: Format and show the code commit**

Run: `make cpp-format && make py-lint-fix`, then show the human agent `git diff` of `combinatorics.cpp`, `test_combinatorics.cpp`, `smoke_stress.cpp`, `test_smoke.py`, and wait for approval.

```bash
git add src/native/lib/calc/combinatorics.cpp src/native/tests/unit/test_combinatorics.cpp src/native/tests/smoke/smoke_stress.cpp tests/py/smoke/test_smoke.py
git commit -m "fix/native: nPr and nCr in closed form, no loop to freeze on"
```

### Task 3: Docs commit

**Files:**
- Commit: `docs/superpowers/specs/2026-11-16-combinatorics-closed-form-design.md`, `docs/superpowers/plans/2026-11-16-combinatorics-closed-form.md`, `docs/superpowers/findings/combinatorics.md`, `docs/superpowers/findings/README.md`

- [ ] **Step 1: Check the docs against the code as built**

Read the spec, the findings and this plan against the Task 1 and 2 diff; any name, value or claim that changed is fixed now. No em dash (U+2014) in the four files.

- [ ] **Step 2: Show the diff and wait for approval, then commit**

```bash
git add docs/superpowers/specs/2026-11-16-combinatorics-closed-form-design.md docs/superpowers/plans/2026-11-16-combinatorics-closed-form.md docs/superpowers/findings/combinatorics.md docs/superpowers/findings/README.md
git commit -m "docs/native: combinatorics closed form spec, plan and findings"
```
