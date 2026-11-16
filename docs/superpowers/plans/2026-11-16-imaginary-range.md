# Imaginary Range Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An imaginary literal keeps a BigReal magnitude as a BigComplex, and a Cx result that leaves the double range is widened to BigComplex (#239).

**Architecture:** Two native changes in the evaluator: the imaginary branch of `literal_value` (`src/native/lib/eval/literal.cpp`), and `promote_range` (`src/native/lib/eval/eval.cpp`) reading a `Complex` result beside its `double` one. `coerce`, `promote_big`, `promote_complex` and the narrowings do not change.

**Tech Stack:** C++ native core (Boost Multiprecision `cpp_dec_float` / `cpp_complex_50`), pybind11, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-imaginary-range-design.md`. Findings: `docs/superpowers/findings/imaginary-range.md`.

## Global Constraints

- Rows go into the existing tables; no new test structure, no new test file.
- Every bug row fails before its fix and passes after it; the guard rows pass before and after.
- No change to `coerce`, `promote_big`, `promote_complex`, `escaped_double_range`'s behavior on a double, or any narrowing.
- No helper, guard or branch that no row below takes (`docs/rules/ai/bugs.md`).
- `make native-build` after every C++ change. Never run clang-tidy.
- No commit without the human agent's approval of its diff; a subagent stops at the commit step.

## Review Focus

- A zero that is the answer stays a Complex: `i*i` is `-1+0i`, `(1+i)-(1+i)` and `0i*5` are `0`. Guard rows in Task 2.
- An imaginary literal a double holds stays a Complex: `3i`, `-2i`, `2.5i`, `1e300i`. The existing `literal_cases` rows and the e2e `const-imaginary-unit` rows cover `i`, `3i`, `-2i`; Task 1 adds `1e300i` to `literal_arm_cases` with arm `Cx`.
- An op with no BigCx arm keeps its Complex result: `sinh(1000+i)` stays `inf+infi`. Task 2 adds the row.
- A Double result keeps today's behavior: the existing `range_promotion_arm_cases` and `range_promotion_value_cases` rows stay green.
- A complex whose parts a double holds keeps its arm even when its modulus would not fit: `1.5e308+1.5e308i` stays a Complex. Task 2 adds the value row.
- The spelling does not change the value: `1e400i`, `i1e400` and `1e400*i` all give `0+1e+400i`. Task 1's e2e rows.

## Before Task 1

The human agent creates the branch: `git switch -c fix/imaginary-range origin/master`. The uncommitted findings, index line, spec and this plan come with it. `make native-build`.

### Task 1: The imaginary literal keeps a BigReal magnitude

**Files:**
- Modify: `src/native/lib/eval/literal.cpp:187-202` (the imaginary branch of `literal_value`)
- Test: `src/native/tests/unit/test_eval.cpp:561` (`literal_arm_cases`)
- Test: `tests/py/e2e/test_eval_e2e.py` (`test_native_eval_golden`, a new section after the `sqrt(10^{-400})` row, before `# a negative base under a root's exponent`)

**Interfaces:**
- Consumes: `parse_real` (same file), `detail::BigComplexComponent` (`src/native/lib/value.hpp:144`).
- Produces: `literal_value("1e400i")` is a `BigComplex` with real part 0 and imaginary part the BigReal `1e400` converted through `detail::BigComplexComponent`.

- [ ] **Step 1: Write the failing native rows**

In `literal_arm_cases`, after `"a huge exponent does not hang"`:

```cpp
{.id = "an imaginary exponent past double", .input = "1e400i", .expected = Arm::BigCx},
{.id = "an underflowing imaginary exponent", .input = "1e-400i", .expected = Arm::BigCx},
{.id = "an imaginary integer past int64", .input = "99999999999999999999i", .expected = Arm::BigCx},
{.id = "an imaginary exponent a double holds", .input = "1e300i", .expected = Arm::Cx},
```

- [ ] **Step 2: Write the failing e2e rows**

A section comment `# an imaginary literal or a complex result past double's range -> BigComplex`, then:

```python
param("1e400i", "BigComplex", "0+1e+400i", id="imaginary-literal-past-double"),
param("i1e400", "BigComplex", "0+1e+400i", id="imaginary-constant-past-double"),
param("1e-400i", "BigComplex", "0+1e-400i", id="imaginary-literal-underflow"),
param("1e400i-1e400i", "BigComplex", "0+0i", id="imaginary-literal-past-double-cancels"),
param("(1e400i)^{2}", "BigComplex", "-1e+800+0i", id="imaginary-literal-past-double-squared"),
param("1e400+1e400i", "BigComplex", "1e+400+1e+400i", id="bigreal-plus-imaginary-literal"),
```

`i1e400` is green before the fix; it pins that both spellings agree.

- [ ] **Step 3: Run them and see them fail**

Run: `make native-build && make native-test`
Expected: the run fails on exactly the three `BigCx` rows above (the literal is `Cx`); `1e300i` passes.

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -k "imaginary-literal or imaginary-constant-past-double or bigreal-plus-imaginary-literal"`
Expected: 5 failed (type `complex`), `imaginary-constant-past-double` passed.

- [ ] **Step 4: Implement**

In the imaginary branch, a BigReal from `parse_real` returns `Value{BigComplex(detail::BigComplexComponent(0), detail::BigComplexComponent(big))}`: the construction `detail::real_to_big_complex` (`value.hpp:148`) already uses, with the parts swapped. Its comment says why the component wrap is needed (BigReal's backend does not convert to the component type on its own). No new helper: it is one construction in one place, and `real_to_big_complex` builds a real part, not an imaginary one. The Int64 and Double arms keep `Complex(0.0, to_double(...))`; the comment above the three branches ("the arms to_double already has an overload for") is rewritten to say the BigReal one keeps its magnitude. The prefix form (`i3`) stays as it is.

- [ ] **Step 5: Run and see them pass**

Run the two commands of Step 3. Expected: all rows pass; `make native-test` reports no failure.

- [ ] **Step 6: Commit (after the human agent approves the diff)**

`make cpp-format && make py-lint-fix`, show the diff, then:

```bash
git add src/native/lib/eval/literal.cpp src/native/tests/unit/test_eval.cpp tests/py/e2e/test_eval_e2e.py
git commit -m "fix/eval: an imaginary literal keeps a BigReal magnitude"
```

### Task 2: Range promotion reads a Complex result

**Files:**
- Modify: `src/native/lib/eval/eval.cpp:144-191` (`escaped_double_range`, `redispatch_big`, `promote_range`)
- Test: `src/native/tests/unit/test_eval.cpp:443` (`range_promotion_arm_cases`), `:471` (`range_promotion_value_cases`)
- Test: `tests/py/e2e/test_eval_e2e.py` (the section Task 1 opened)

**Interfaces:**
- Consumes: `lift_to_big` (`eval.cpp:97`), `lift_to_big_complex` (`eval.cpp:84`), `any_operand_zero` (`eval.cpp:127`), `escaped_double_range` (`eval.cpp:144`), `redispatch_big` (`eval.cpp:158`), `ops::has_trait(id, ops::Trait::ExactZero)`, `ops::arms_of`, `has_arm`.
- Produces: `promote_range` returns a BigComplex for a Complex result that escaped the double range when the op has a BigCx arm; otherwise its input unchanged. Signatures of `promote_range` and `apply` do not change.

- [ ] **Step 1: Write the failing native rows**

In `range_promotion_arm_cases`, arm `Arm::BigCx`:

| id | op | args |
|---|---|---|
| mul(1e200i, 1e200i) overflows into BigComplex | Mul | Complex(0, 1e200), Complex(0, 1e200) |
| add(1e308i, 1e308i) overflows into BigComplex | Add | Complex(0, 1e308), Complex(0, 1e308) |
| mul(1e-200i, 1e-200i) underflows into BigComplex | Mul | Complex(0, 1e-200), Complex(0, 1e-200) |
| mul(1e-160i, 1e-160i) goes subnormal into BigComplex | Mul | Complex(0, 1e-160), Complex(0, 1e-160) |
| mul of 1e300+1e300i by itself overflows into BigComplex | Mul | Complex(1e300, 1e300) twice |
| pow(2i, 2000) overflows into BigComplex | Pow | Complex(0, 2), Complex(2000, 0) |
| exp(1000+i) overflows into BigComplex | Exp | Complex(1000, 1) |

Arm `Arm::Cx`, the op with no BigCx arm: `sinh(1000+i) keeps its Complex`, Sinh, `Complex(1000, 1)`.

In `range_promotion_value_cases`, green before and after:

| id | op | args | expected |
|---|---|---|---|
| mul(i, i) keeps a zero part | Mul | Complex(0, 1) twice | Complex(-1, 0) |
| sub(1+i, 1+i) keeps a difference's zero | Sub | Complex(1, 1) twice | Complex(0, 0) |
| mul(0, 5) keeps a complex zero operand's zero | Mul | Complex(0, 0), Complex(5, 0) | Complex(0, 0) |
| add(1.5e308, 1.5e308i) keeps parts a double holds | Add | Complex(1.5e308, 0), Complex(0, 1.5e308) | Complex(1.5e308, 1.5e308) |

- [ ] **Step 2: Write the failing e2e rows**

In Task 1's section:

```python
param("1e200i*1e200i", "BigComplex", "-9.999999999999999e+399+0i", id="complex-mul-overflow"),
param("1e-200i*1e-200i", "BigComplex", "-1e-400+0i", id="complex-mul-underflow"),
param("(2i)^{2000}", "BigComplex", "1.148130695274255e+602+0i", id="complex-pow-overflow"),
param("exp(1000+i)", "BigComplex", "1.064433965627625e+434+1.657757680453514e+434i", id="complex-exp-overflow"),
```

`1e200i*1e200i` is the double `1e200` widened, the digits `1e200*1e200` gives today (spec, Tests).

- [ ] **Step 3: Run them and see them fail**

Run: `make native-build && make native-test`
Expected: the run fails on exactly the 7 BigComplex rows (arm `Cx`); the Sinh row and the 4 value rows pass.

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -k "complex-mul-overflow or complex-mul-underflow or complex-pow-overflow or complex-exp-overflow" -q`
Expected: 4 failed.

- [ ] **Step 4: Implement**

Every piece exists; the change hoists two of them and adds one overload.

- `escaped_double_range(double, args, exact_zero)`: its first two tests (`std::isinf`, `FP_SUBNORMAL`) move into a one-line `bool outside_double_range(double)` in the same anonymous namespace, which the double overload calls. A second overload `escaped_double_range(const Complex &, args, exact_zero)` calls it on each part, then makes the same `exact_zero` and zero test as the double one on the whole value (`c == 0.0`). Not `std::abs(c)` as one double: its modulus is `inf` for `1.5e308+1.5e308i`, whose parts are finite and which is right today (measured), so that result would change arm.
- `redispatch_big` takes the lift as a last parameter, `Value (*lift)(const Value &)`; the double caller passes `lift_to_big`, the Complex caller `lift_to_big_complex`. No second redispatch function.
- `promote_range`: the body today reads `double`, `Arm::Big`, `lift_to_big`, `BigReal`. It becomes one function template over the narrow and the wide type, `template <class Narrow, class Wide> Value widen_escaped(OpId, const Calculator &, const std::vector<Value> &, Value result, const Narrow &, Arm, Value (*lift)(const Value &), Calculator::AngleUnit)`, holding today's body unchanged with those four names as parameters. `promote_range` tells the arm apart once: a `double` result calls it with `<double, BigReal>`, `Arm::Big`, `lift_to_big`; a `Complex` result with `<Complex, BigComplex>`, `Arm::BigCx`, `lift_to_big_complex`; any other result returns as it is. The widened-zero test stays `*w == 0`: it compiles and reads right on a `BigComplex` (`BigComplex(0, 0) == 0` is true, `BigComplex(0, 1) == 0` false, probed).

No `nan` test and no change to `any_operand_zero` (spec, The fix 2).

- [ ] **Step 5: Run and see them pass**

Run the two commands of Step 3, then the whole e2e file: `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q`
Expected: all pass; `make native-test` reports no failure.

- [ ] **Step 6: Commit (after the human agent approves the diff)**

`make cpp-format && make py-lint-fix`, show the diff, then:

```bash
git add src/native/lib/eval/eval.cpp src/native/tests/unit/test_eval.cpp tests/py/e2e/test_eval_e2e.py
git commit -m "fix/eval: widen a complex result past the double range"
```

### Task 3: Findings and docs

**Files:**
- Modify: `docs/superpowers/findings/imaginary-range.md`

- [ ] **Step 1: Record the result**

A dated entry with the branch and commit: the rows of both bugs after the fix, from the e2e rows of Tasks 1 and 2 (`PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py -q -k "imaginary-literal or imaginary-constant or bigreal-plus-imaginary or complex-mul-overflow or complex-mul-underflow or complex-pow-overflow or complex-exp-overflow"`), and the native test count.

- [ ] **Step 2: Commit (after approval)**

The findings, its index line, the spec and this plan go in one docs commit: `docs/eval: imaginary range spec, plan and findings`.

The last sentence of the glossary entry `Overflow`, "A complex result is not widened this way", no longer holds after Task 2. Glossary changes go on the `docs/glossary-additions` branch, not here; the human agent decides when.
