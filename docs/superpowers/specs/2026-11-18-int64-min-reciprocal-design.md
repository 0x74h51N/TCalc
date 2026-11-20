# The reciprocal of INT64_MIN is a math error the retry catches

Issue #249, milestone First release. Measurements: [int64-min-reciprocal.md](../findings/int64-min-reciprocal.md).

## The bug

int64 holds `-9223372036854775807-1` but not `9223372036854775808`. Three places take a reciprocal by swapping numerator and denominator, `Rational(den, num)`. With `-9223372036854775807-1` as the numerator, `boost::rational` negates it to move the sign to the denominator, cannot, and throws `boost::bad_rational`. That is no `CalculatorError`, so the retry in `apply` never sees it: the binding raises `ValueError`, and the controller's catch-all (`controller.py:308`) shows `Invalid inputs`.

## How a case flows today

`apply` (`eval.cpp`) runs in this order:

1. The real-first rewrite (`eval.cpp:416-430`), only for a negative real first operand and a fractional `Rational` second one. A root (`Trait::InverseDegree`) becomes `apply(Pow, x, 1/degree)` (line 423); a power with an odd denominator (`Trait::RootExponent`) becomes `apply(Pow, x, p)` and then `apply(Root, ..., q)` (lines 427-428).
2. `promote_big`, `coerce`, `promote_complex`.
3. The kernel call inside `try` (line 447). A `CalculatorError` from the exact `Rational` arm is caught: the row's retry arm (`ops::retry_arm_of`) lifts the operands to BigReal, or without one to double (`ops.hpp:963`), and the kernel runs again.

The exact kernels: `Calculator::pow(Rational, Rational)` (`arithmetic.cpp:155`) sends a fractional exponent to `calc_detail::try_rational_pow` and runs a whole one by repeated squaring, then swaps a negative exponent's result at line 197. `Calculator::root(Rational, Rational)` (`arithmetic.cpp:203`) swaps the degree at line 205 and hands the reciprocal to `try_rational_pow`, which calls `Calculator::pow` with the numerator of that exponent (`helpers.hpp:374` for a whole one, `:381` for a fractional one). `Recip` is `pow(x, kReciprocal)` (`ops.hpp:1193`).

## Where each case throws

M is `-9223372036854775807-1`. Each case raises `ValueError` e2e on b00725b. The throw site is the stack at the throw (`gdb -batch -ex "catch throw" -ex run -ex bt`). Expected values: mpmath, 60 digits; an even degree of a negative radicand gives the principal value. The first nine are the 16 smoke pins (`\root` and `⌄` are one op); the last five were found since.

| Input | Op | Throws at | Reached through | Expected |
|---|---|---|---|---|
| (M)^(-1) | Pow | arithmetic.cpp:197 | kernel, eval.cpp:447 | -1.0842021724855044e-19 |
| (M)⁻¹ | Recip | arithmetic.cpp:197 | kernel, eval.cpp:447 | -1.0842021724855044e-19 |
| (1)⌄(M) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 1 |
| (-1)⌄(M) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 1-3.4061215800865546e-19i |
| (0.5)⌄(M) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 1.000000000000000000075151 |
| (1/3)⌄(M) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 1.000000000000000000119112 |
| (9223372036854775807)⌄(M) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 0.9999999999999999952654764 |
| (M)⌄(-1) | Root | arithmetic.cpp:197 | root, try_rational_pow (helpers.hpp:374), kernel | -1.0842021724855044e-19 |
| (M)⌄(M) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 0.9999999999999999952654764-3.4061215800865546e-19i |
| (M)^(-1/3) | Pow | arithmetic.cpp:197 | real-first, eval.cpp:427, then kernel | -1/2097152 |
| (M/3)⌄(-8) | Root | arithmetic.cpp:197 | root, try_rational_pow (helpers.hpp:381), kernel | 0.0045148599892078299-0.0018701162397455287i |
| (8)⌄(M/3) | Root | arithmetic.cpp:205 | kernel, eval.cpp:447 | 0.9999999999999999993236395 |
| (-8)⌄(M/3) | Root | eval.cpp:423 | real-first, before the kernel | 0.9999999999999999993236395-1.021836474025966376e-18i |
| (M/3)⁻¹ | Recip | arithmetic.cpp:197 | kernel, eval.cpp:447 | -3.252606517456513302022358e-19 |

## The fix

Two of the three sites are inside the kernel, so a `CalculatorError` there is caught by the retry. The reciprocal goes through the existing `Calculator::div(Rational, Rational)` (`arithmetic.cpp:139`): it computes in `calc_detail::WideRational`, narrows back with `calc_detail::narrow` and raises `calc_detail::math_error()` when the result does not fit, the same as `add`, `sub` and `mul`.

1. `arithmetic.cpp:196-200`: the negative exponent's swap becomes `return div(Rational(1), Rational(result));` inside the existing `if (neg_exp)`.
2. `arithmetic.cpp:205`: `const Rational inv = div(Rational(1), b);`.

The third site runs before the kernel, outside the `try`, so a `math_error` there would reach the user as `Math Error` and no retry would run. When the degree's reciprocal does not fit, the rewrite is skipped and the op takes the ordinary path, where the kernel's `root` raises the error of fix 2 inside the `try`:

3. `eval.cpp:419-424`: the reciprocal is `calc_detail::narrow(calc_detail::WideRational(1) / calc_detail::widen(*e))`, and the `return apply(c, OpId::Pow, ...)` runs only when it holds a value. The input that takes the other branch is `(-8)⌄(M/3)`. `widen` and `narrow` reach `eval.cpp` through `parser/pub/ops.hpp`, which includes `calc/internal/helpers.hpp`, as `calc_detail::whole` already does.

4. `helpers.hpp`, `try_rational_pow`: a fractional exponent `p/q` takes the exact `q`-th root of the base before its `p`-th power. Added after the final review: `M⌄(-3)` built `M⁻¹` first and retried in double, 4 ulps off `-1/2097152`; with the root first it is `Rational(-1, 2097152)`. `p/q` is in lowest terms, so the base's `p`-th power is a perfect `q`-th power exactly when the base is.

No header, helper, function or class is added or renamed, and no other check is added. The other branch of fix 3, a reciprocal that fits, keeps its rewrite: the existing rows `root-reciprocal-degree-huge-negative`, `root-reciprocal-degree-huge-positive` and `root-reciprocal-degree-negative-double` take it, and `(-8)⌄(1/3)` is `Rational -512` (measured on b00725b) as a row in `test_stays_rational`, green before and after.

## What the user sees

Each case gives a value instead of `Invalid inputs`. The result type follows the row's retry arm: `Pow` with a whole exponent retries in BigReal (`power_retry_arm`, `ops.hpp:1071`), `Recip` and `Root` have none and retry in double, and a negative radicand at an even degree goes complex through `promote_complex`. This is read from the code and confirmed by the tests' run.

## Not in this spec

- The precision of the retry. A refused exact root retries in double, and a root near 1 loses its small part: #231 (comment of 2026-11-18) and #263. A row whose Expected the retried type cannot hold keeps only the double's digits after this fix; #231 owns the rest.
- A native throws row. `EXPECT_THROWS` catches any exception (`test_helpers.hpp:597`), so a throws row for `pow` or `root` passes before the fix too and proves nothing.

## Tests

Written before the fix, red first.

- End to end, `tests/py/e2e/test_eval_e2e.py`, `test_native_eval_golden`: one row per case above, its id ending in `recip-i64-min`, with its Expected value and the type of its retry arm. Before the fix every row raises `ValueError`. If the run after the fix gives another type, or a value off from the Expected beyond what the type holds, it is reported before any row changes. The golden table compares a float or a complex with `pytest.approx`, so a row whose Expected a double cannot hold (a root near 1) passes at the double's value; one comment over those rows names #231.
- `tests/py/smoke/test_smoke.py`: the 16 #249 pins are `xfail(strict=True)`, so after the fix each one fails as an unexpected pass; that is their green, and they leave `SMOKE_PINS`.
- `src/native/tests/smoke/smoke_stress.cpp`: the 10 #249 entries of `kSmokePins` fail as "pinned case passes" after the fix and leave the table. With no case failing, the smoke builder read `f->second` at `failures.end()` and the run segfaulted, so `expect_msg` (`tests/internal/test_helpers.hpp`) builds its message only on a failure, which is the only time `expect_true` reads it.
- Native, `src/native/tests/unit/test_eval.cpp`, full precision: `apply` on the op, `tol` 0, arm and value. `range_promotion_value_cases`: `pow(M,-1)` is `BigReal("-1.08420217248550443400745280086994171142578125e-19")`; `recip(M)` and `root(M,-1)` are `-1.0842021724855044e-19`, `recip(M/3)` `-3.2526065174565133e-19`; `root(x, M)` for x in 1, 1/2, 1/3, int64 max, and `root(8, M/3)`, are `1.0`. `negative_base_apply_cases`: `root(-1, M)` and `root(M, M)` are `Complex(1.0, -3.4061215800865545e-19)`, `root(-8, M/3)` `Complex(1.0, -1.0218364740259663e-18)`, `root(M/3, -8)` `Complex(0.00451485998920783, -0.0018701162397455288)`. Each is the correctly rounded value of the exact one (mpmath, 80 digits). `root(M, -3)` is `Rational(-1, 2097152)` (fix 4). `pow(M, -1/3)` goes through the real-first rewrite to a BigReal root, and `root(BigReal, BigReal)` is `pow(x, 1/y)` with `1/3` rounded, `2.9e-63` off `-1/2097152`: its row expects the exact BigReal and is commented out with a TODO until the BigReal arm roots an integer degree exactly.
- A wrong value after the fix runs on `calc_native.apply`, `format_result` and the native layer to find its source, as `docs/rules/ai/tests.md` says.
- Run: `make native-build`, `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py`, `make py-smoke`.
