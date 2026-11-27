# gcd and lcm past int64 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gcd and lcm give the right integer for every whole operand, Int64, double or BigReal, never abort, and say `needs multiprecision mode` where the integer cannot be held exactly (#247).

**Architecture:** Two arms in `calc/number_theory.cpp`: arm 1 folds `std::uint64_t` magnitudes, arm 2 folds `cpp_int` with Boost's `gcd` and `lcm`. A call rule in `eval/exact.cpp` reads a power or a factorial argument from its own base and exponent or n, each evaluated once, before the value is rounded to BigReal's 73 digits.

**Tech Stack:** C++20, Boost.Multiprecision (`cpp_int`, `int256_t`, `cpp_dec_float`), the native test runner, pytest.

**Spec:** `docs/superpowers/specs/2026-11-24-gcd-lcm-past-int64-design.md`

## Global Constraints

- No commit without the human agent's approval: every commit step stops, shows the files and the diff, and waits. Before it, `make cpp-format` and `make py-lint-fix`.
- Never run clang-tidy; the pre-push hook runs it.
- No magic number in native code: every literal is a named `constexpr`; $2^{53}$ is the existing `kExactIntLimit`.
- `make native-build` after every C++ change; run the tests of what changed, not `make py-test`.
- A BigReal is read through the exact `whole`; `snapped_whole` is not used here.
- An integer goes into BigReal only from text with its exponent; never `BigReal(int512_t)` and never a product with `pow(BigReal(10), p)`.
- An integer BigReal cannot hold exactly is `needs multiprecision mode`; a value that is no integer at any precision is `only defined for integers` (the human agent's rules).

## Review Focus

- An lcm of three operands past BigReal's digits, folded again: `lcm(10^{70}+1,10^{70}+3,10^{70}+7,10^{70}+1)` within a relative `1e-72` of the exact value.
- A single negative operand: `gcd(-10^{19})` is `1e19`, positive.
- A power argument whose base is an expensive expression is evaluated once: `gcd((\sum_{n=1}^{100000}gcd(n,6))^{8},2)` costs what the power alone costs.
- A power past the bound beside a zero: `gcd(2^{9223372036854775807},0)` is `needs multiprecision mode`, not a crash in `powm`.
- The same bit length gets one answer: `lcm(19^{3857},1)` and `lcm(2^{16384},1)` are both built.

### Task 1: Commit the tree as it stands

- [x] **The probe rows:** f4dc833, `chore/probe: boost rows for the gcd and lcm measurements, --time on boost`.
- [x] **The whole split:** 7d6d4d0, `refactor/calc: whole reads a BigReal exactly, snapped_whole keeps the snap`. Produces `bool calc_detail::whole(const BigReal &y)` (exact, `floor(y) == y`) and `snapped_whole` for the six callers that keep the snap.

### Task 2: The two arms

f68f447, `fix/calc: gcd and lcm past int64 fold magnitudes and a factored integer`. Arm 2 was a factored `int512_t`; Task 3 replaced it with `cpp_int`.

**Files:** `src/native/lib/calc/number_theory.cpp`; tests in `src/native/tests/unit/test_number_theory.cpp`, `tests/py/e2e/test_eval_e2e.py`, `tests/py/e2e/test_reductions_e2e.py`.

**Interfaces** (anonymous namespace of `number_theory.cpp`):
- `std::optional<std::uint64_t> small_magnitude(const CollectionItem &it)`: an Int64's magnitude, a double's when `int_like(d)` and $|d| < 2^{53}$.
- `small_gcd`, `small_lcm` (empty past `std::uint64_t`, the product in `int256_t`).
- `CollectionItem fold_integers(const Collection &a, const char *name, SmallStep small, calc_detail::BigStep big)`; `Calculator::gcd` and `Calculator::lcm` are one call each.

- [x] Native table of gcd and lcm rows, red first; the #250 rows that expected a throw replaced.
- [x] e2e rows of the issue's table, red first.
- [x] Green: `make native-test`, the two e2e files.
- [x] Timing against master (Release, measured again on 28c0ca7): `gcd(12,8)` 306 ns on master, 333 ns here.

### Task 3: Powers and factorials read from their tokens

3a9a8e0, `fix/eval: gcd and lcm read a power or a factorial from its tokens`.

**Files:** `src/native/lib/calc/internal/helpers.hpp`, `src/native/lib/calc/number_theory.cpp`, `src/native/lib/calc/pub/error_messages.hpp`, `src/native/lib/eval/internal/exact.hpp`, `src/native/lib/eval/exact.cpp`, `src/native/lib/eval/eval.cpp`, and the three test files.

**Interfaces:**
- `exact.hpp`: `using CallRule = std::optional<Value> (*)(ops::OpId, std::span<const parser::ParenElement>, const Calculator &, Calculator::AngleUnit);`, `CallRule call_rule(OpId id)`; `ExactRow` gets `CallRule from_call`.
- `helpers.hpp`, `calc_detail`: `kMaxIntBits` (16384), `magnitude`, the `whole_operand` overloads (Int64, double, BigReal, Rational), `int_operand` (one visit for a `CollectionItem` and a `Value`), `BigStep`, `gcd_of`, `lcm_of`, `item_of`.

- [x] Arm 2 on `cpp_int` with `mp::gcd` and `mp::lcm`; `Factored` removed (the human agent: Boost already has them).
- [x] A BigReal from $10^{72}$ is `needs multiprecision mode`; a value that is not whole is `only defined for integers`.
- [x] The call rule reads a power or a factorial argument from its tokens; the collection conversion stays in `eval.cpp`.
- [x] Red rows first, then green: `make native-test`, the two e2e files.

### Task 4: The whole-branch review

3cb377a, `fix/eval: gcd and lcm evaluate each argument once and bound an lcm`.

- [x] The call rule runs before `call_operands` and evaluates every argument itself, once: a power's base and exponent, a factorial's n (`gcd((\sum_{n=1}^{100000}gcd(n,6))^{8},2)` 126 ms to 62.4 ms).
- [x] `lcm_of` throws `needs multiprecision mode` past `kMaxIntBits` (a 20-argument lcm took 409 ms; up to the bound a 40-argument one takes 1.0 ms).
- [x] `rounded_big`: a large result reads into BigReal from its leading 100 digits (0.8 ms to 0.02 ms at 16384 bits).
- [x] A leading minus on a power or a factorial argument is read (`gcd(-2^{265},3)` is `1`).
- [x] Tests compare a BigReal result with `decimal_text(out, 100)` within `1e-72`; the guards each have a row, shown red without them.

### Task 5: powm and the no-integer rule

28c0ca7, `fix/eval: gcd reads a power past the bound modulo the others, a non-integer power or factorial is integers_only`.

**Interfaces** (`calc_detail`): `using PowerStep = cpp_int (*)(const std::optional<cpp_int> &, std::uint64_t, std::uint64_t);`, `gcd_power` (`powm` against the fold of the others), `lcm_power`.

- [x] A power past the bound is a `HugePower`, folded last: `gcd(2^{9223372036854775807},12)` is `4`.
- [x] A fraction's positive power, an integer's inexact root and a fraction's factorial are `only defined for integers`, thrown in their place in the fold.
- [x] The final review's fixes: one msb bound for powers, factorials and lcm; one magnitude visitor; the Pow latex rule read from the table; the leading minus no longer applied to the value; `Arg` visited.

### Task 6: The spec table and the smoke runs

- [x] Every row of the spec's case table through `tokenize`, `evaluate_branch` and `format_result`, on master and on 28c0ca7: the table in the spec.
- [x] `make native-test` (13178 passed) and `make py-smoke` (10881 passed), no pin added.
- [ ] Look at the results in the app.
