# An exact result past int64 widens into BigReal

Issues #245 (an exact Rational result) and #252 (`intdiv`), milestone First release. Measurements: [rational-overflow.md](../findings/rational-overflow.md).

## The bug

A double holds an integer exactly only up to $2^{53}$. Two paths put an integer past int64 into a double, and the value is wrong from there; every op after it carries the error.

#245, an exact result past int64 is computed again in double:

- `3^{40}-12157665459056928801` is `-33`, exact 0.
- `9223372036854775807+2-9223372036854775809` is `-1`, exact 0.
- `3037000500*3037000500-9223372037000250000` is `-656`, exact 0.
- `(1/3)^{40}*3^{40}` is `0.999999999999998`, exact 1.
- `10^{23}` is `1.0000000000000001e+23` and `10^{200}` is `9.9999999999999997e+199`.
- `(1/3)^{-40}` is `1.2157665459056955e+19`, and `3^{40}` is `1.2157665459056929e+19`: the same number, two values.

#252, `intdiv` divides in double and casts with no range check:

- `intdiv(9223372036854775807,1)`, `intdiv(1e19,1)` and `intdiv(1e300,1)` are `-9.223372036854775808e+18`.
- `intdiv(1e19,3)` is `3.333333333333333504e+18`, exact 3333333333333333333.
- `intdiv(9007199254740993,1)` is `9007199254740992`, and `intdiv(9223372036854775807,1099511627776)` is `8388608`, exact 8388607: the operand loses its last digit before the division, so a small quotient is wrong too.

## How these values flow today

The Rational arm of Add, Sub, Mul and Div computes in `WideRational` and narrows back with `narrow` (`calc/internal/helpers.hpp`); Pow checks `rational_pow_overflows` first. When the result does not fit int64, each throws `math_error()`. An irrational answer throws the same error: Pow with an exponent whose root is not exact, Root, Sqrt, Cbrt, Log.

`apply` (`eval/eval.cpp`) catches it when a dispatched operand is a Rational, converts every operand with `as_double`, runs `promote_complex`, and runs the kernel again in double. `promote_range` then reads the double result, but a finite, normal double such as `1.2157665459056929e+19` shows none of its signs (inf, subnormal, a zero from operands that are not zero), so it stays.

`intdiv` has a double and a BigReal kernel and no Rational one (`calc/pub/calculator.hpp`). An Int64 or Rational operand is coerced to double; the double kernel returns `static_cast<long long>(a / b)`, which past int64 is undefined behavior (INT64_MIN on x86-64). Called directly, `intdiv(9223372036854775807.0, 1.0)` is `-9223372036854775808`; the BigReal kernel gives `intdiv(BigReal("9223372036854775807"), BigReal("1099511627776"))` = `8388607` and `intdiv(BigReal(1e19), BigReal(3))` = `3333333333333333333`.

`promote_big` widens the operands to BigReal before coerce when the op's row has a range rule (`with_range`) and the rule holds for the operands as they arrived. Only Pow (`power_needs_big`, a result past $10^{308}$ or base 10 with an exponent of 308 or more) and Root have one.

The BigReal arm holds these values: `apply(Sub, apply(Pow, BigReal(3), BigReal(40)), BigReal(12157665459056928801))` is `BigReal 0`. It is exact up to 50 significant digits and rounds past them.

## Approaches

- #245, the retry widens into BigReal when the exact answer is rational (chosen): the exact arm can then only have failed by overflow, and BigReal holds the value the double loses. An irrational answer keeps today's double retry.
- #245, the retry stays in double and range promotion widens the result: rejected, the double result shows no sign of escape, the operands are doubles by then so a $2^{53}$ test would also widen a typed `1e20*3`, and a small result with an overflowed denominator (`(1/3)^{40}`, `8.2e-20`) would pass any magnitude test.
- #245, a Rational on a wider integer: rejected for this bug, it changes the whole Rational arm, the bindings and the stubs.
- #252, an exact `intdiv` kernel on Rational operands that returns int64 (chosen, after review): the quotient of two integers or fractions is computed whole, so no operand is read as a double, and the result stays an integer.
- #252, a range rule on the `intdiv` row that widens Int64 and Rational operands to BigReal by their magnitude (the first version, replaced): `intdiv(10^{18},10^{18})` became `BigReal 1`, and `atan` of it failed, since `atan` has no BigReal arm; `intdiv(2^{62},3)` stayed wrong below the bound.
- #252, an exact kernel that returns a Rational: rejected, an integer quotient would be stored as `x/1`.
- #252, a range check inside the double kernel: rejected, by then the operand has already lost its digit (`9007199254740993` is `9007199254740992`), and the kernel could only throw, not widen.
- #252, the double kernel returns `std::trunc(a / b)` as a double, with no cast: rejected, the result leaves the Int64 arm and the next op is no longer exact. `intdiv(7,2)/2` is `Rational 3/2` today, while `trunc(7/2)/2`, whose kernel returns a double, is `float 1.5`.

## The fix

### 1. Which ops have a rational answer (#245)

Whether the exact answer is rational is a fact of the op, so it lives in the op's row of the ops table, beside the range and domain rules (`with_range`, `with_domain`). A row names it with a rule over its two Rational operands:

- Add, Sub, Mul, Div: always rational.
- Pow: rational when the exponent is whole.

Every other row names none, and its retry stays in double.

### 2. The retry reads the rule (#245)

In `apply`'s catch, when the op's rule holds for the Rational operands the kernel ran with, the operands are lifted with the existing `lift_to_big` and the kernel runs again in BigReal; otherwise the retry is the double one it is today. A second throw propagates, as it does today (`0^{-1}` stays a math error). `promote_range` follows either retry unchanged.

### 3. intdiv of integers runs exact (#252)

`intdiv` gets a Rational kernel, `std::int64_t intdiv(const Rational &, const Rational &)`: it divides in the existing `WideRational`, truncates toward zero as the double and BigReal kernels do, and returns the quotient as int64. A quotient past int64 overflows it, as `intdiv(INT64_MIN, -1)` and `intdiv(INT64_MAX, 1/2)` do; its row retries in BigReal (`retry_in_big`). The row keeps its range rule for doubles: it holds when an operand or the quotient is $2^{53}$ or more in magnitude, and `promote_big` then lifts the operands to BigReal. A new `Trait::DoubleKernelRange` on the row tells `promote_big` that the rule guards only the double kernel, so Int64 and Rational operands skip it and reach the exact kernel. A zero divisor is the same math error as today.

### 4. Nothing else changes

`promote_complex`, `promote_range`, the other Rational kernels and the formatter stay as they are. `coerce` runs an op with no BigReal arm (`atan`, `asin`, `acos`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `cbrt`, `∠`) in double when every BigReal operand converts to a double that neither overflows nor loses its range; a BigReal past that range is still an error. Without it the fix turned `atan(3^{40})`, which master answers in double, into an error. A Pow retry reads only the exponent: a whole one retries in BigReal, any other one in double, so a fractional power such as `2^(0.1)` stays a double and `atan` of it works. A Rational result inside int64 stays a Rational; `sqrt(2)` and `2^{1/2}` stay double.

## What the user sees

The value is exact up to 50 digits and stays exact through the next op. The result line shows a BigReal through `str`, 16 significant digits (`3^{40}` shows `1.215766545905693e+19`, the issue expects `12157665459056928801`); showing all of them is #235 and #244.

## Not in this spec

- `sum`, `mean` and `median` of Int64 values past int64: #253. The reductions do not go through `apply`'s retry or `promote_big`.
- gcd and lcm of a value past int64: #247. `gcd(3^{40},3)` is a math error before and after the fix (a double past int64 today, a BigReal with the fix).
- The reciprocal of INT64_MIN: #249.
- An Int64 past $2^{53}$ next to a complex: #240.
- A double total past double's range in sum and mean: #242.
- The zeros the formatter pads an exact integer with (`10^{18}` shows `1.000000000000000000e+18`), and all digits of a BigReal: #244, #235.
- `rational_pow_overflows` refuses some powers that fit int64 (`2^{62}`, `(-2)^{63}`); with the fix they become an exact BigReal instead of a double, not a Rational.
- A result past 50 digits rounds in BigReal (`7^{60}` has 51).
- A Rational whose decimal expansion does not end is rounded to 50 digits when it is lifted, so `(1/3)^{-40}-3^{40}` is `1.8e-46` in BigReal, not 0 (measured with `apply` on BigReal operands).
- The guard-digit noise a BigReal shows when two equal values past 50 digits are subtracted. A power of two past 50 digits now meets it inside double's range: `2^{309}-2^{308}*2` is `float 0` on master and `BigReal -3.8726059e+23` with the fix (measured on a prototype). The same noise is on master past $10^{308}$: `2^{1100}-2^{1099}*2` is `BigReal 4.659688e+262`.

## Tests

Each bug row fails before the fix and passes after it. Rows go into the existing tables. Exact values are computed with Python's integers.

### Native, `src/native/tests/unit/test_eval.cpp`

`range_promotion_arm_cases`, arm `Big`: Pow of `Rational(3)` and `Rational(40)`, Pow of `Rational(1, 3)` and `Rational(40)`, Add of `Rational(INT64_MAX)` and `Rational(2)`, Mul of `Rational(3037000500)` twice, Div of `Rational(INT64_MAX)` and `Rational(1, 2)`, IntDiv of `1e19` and `3.0`, IntDiv of `Rational(INT64_MIN)` and `Rational(-1)`; arm `Int64`: IntDiv of Int64 `INT64_MAX` and Int64 `1`, of Int64 `9007199254740993` and Int64 `1`, of `Rational(10^{18})` twice.

`range_promotion_value_cases`, exact values:

- `pow(2, 64) overflows the exact arm into a double` pins today's double; it becomes `BigReal("18446744073709551616")` and is renamed for what it checks.
- Pow of `Rational(3)` and `Rational(40)` is `BigReal("12157665459056928801")`.
- Mul of `Rational(INT64_MAX)` twice is `BigReal("85070591730234615847396907784232501249")`.
- IntDiv of Int64 `INT64_MAX` and Int64 `1099511627776` is Int64 `8388607`; of Int64 `-INT64_MAX` and Int64 `2` is Int64 `-4611686018427387903`; of `Rational(2^{62})` and `Rational(3)` is Int64 `1537228672809129301`; of `Rational(7, 2)` and `Rational(1, 3)` is Int64 `10`; of `Rational(-7)` and `Rational(2)` is Int64 `-3`.
- IntDiv of `Rational(INT64_MIN)` and `Rational(-1)` is `BigReal("9223372036854775808")`.

The single test `apply :: mul of two small rationals overflows the kernel, recovers as double` becomes arm `Big`, value $6.25 \times 10^{-20}$. `root(2, 2) is irrational, so it falls back to double` stays green, and a row Pow of `Rational(2)` and `Rational(1, 2)` stays a double.

### End to end, `tests/py/e2e/test_eval_e2e.py`

The issues' rows first, with the issues' Expected values. `str` of a BigReal shows 16 digits and the binding has no equality, so a value past 16 digits is checked exact by a difference that must be 0.

`test_native_eval_golden`, type `BigReal`: `10^{23}` is `1e+23`, `10^{200}` is `1e+200`, `10^{200}*10^{200}` is `1e+400`, `10^{19}` is `1e+19`, `3^{40}` and `(1/3)^{-40}` both `1.215766545905693e+19`, `intdiv(1e19,1)` is `1e+19`, `intdiv(1e300,1)` is `1e+300`, `intdiv(1e19,3)` is `3.333333333333333e+18`, `intdiv(-9223372036854775807-1,-1)` is `9.223372036854776e+18`. Type `int`: `intdiv(9223372036854775807,1)`, `intdiv(4611686018427387904,3)` `1537228672809129301`, `intdiv(10^{18},10^{18})` `1`, `intdiv(9007199254740993,1)`, `intdiv(7/2,1/3)` `10`. `atan(intdiv(10^{18},10^{18}))` is `float 0.7853981633974483`, and `atan`, `asin`, `acos`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh` and `atanh` of a fractional power stay a double (or a complex for a negative base). The other side of each bound stays as it is, and these rows pass before and after the fix: in `test_native_eval_golden`, `intdiv(7,2)` int `3`, `intdiv(-7,2)` int `-3` and `intdiv(9007199254740991,1)` int `9007199254740991`; in `TestRational::test_stays_rational`, `3^{39}` is `4052555153018976267/1`, beside the existing `2^61` and `4^(1/2)` rows; in `TestRational::test_raises_math_error`, `intdiv(7,0)`, beside the existing `1/0` and `0^(-1)` rows. `2^{1/2}` stays a double (`pow-frac-exp-sqrt2` in `test_downcasts_to_float`).

`test_bigreal_exact_results`, each a BigReal:

| Expression | Expected |
|---|---|
| 3^{40}-12157665459056928801 | 0 |
| 9223372036854775807+2-9223372036854775809 | 0 |
| -9223372036854775807-2+9223372036854775809 | 0 |
| 3037000500\*3037000500-9223372037000250000 | 0 |
| (-3)^{41}+36472996377170786403 | 0 |
| 7^{23}-27368747340080916343 | 0 |
| 9223372036854775807\*9223372036854775807-85070591730234615847396907784232501249 | 0 |
| 3^{40}\*3^{40}-147808829414345923316083210206383297601 | 0 |
| 9223372036854775807/(1/2)-18446744073709551614 | 0 |
| (1/3)^{40}\*3^{40} | 1 |
| intdiv(-9223372036854775807-1,-1)-9223372036854775808 | 0 |
| intdiv(1e19,3)-3333333333333333333 | 0 |
| intdiv(-1e19,3)+3333333333333333333 | 0 |

Rows that pin today's double and become BigReal (seen red on the prototype, each with the same or a closer value): `pow-large-exp-stays-float` (`2^309`), `float-div-keeps-float` (`(10^307)/(10^306)`), `log-of-its-own-power-implicit-base` (`log(10^{21})`), and in `TestRational::test_downcasts_to_float` the rows `pow-i64-overflow`, `pow-i64-boundary-overflows`, `pow-neg-exp-i64-boundary-overflows`, `pow-frac-overflow` and `rational-denominator-overflows-i64`. Their expected type becomes `BigReal`; a test whose name says it stays float is renamed for what it now checks.

`make native-test` and `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py` run the tests of what changes; any other row whose type changes is reported to the human agent before its expected value is touched.
