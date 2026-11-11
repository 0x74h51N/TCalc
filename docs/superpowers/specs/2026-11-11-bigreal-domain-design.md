# Leaving the real domain past the double range, and the power form of a root

Issue #226, milestone First release. Measurements: [bigreal-domain.md](../findings/bigreal-domain.md).

## The bugs

1. A negative BigReal under sqrt, root at an even or non-integer degree, ln or log is a math error instead of a BigComplex: `sqrt(-1e400)`, `(-1e400)⌄2`, `\root{-10^{400}}{}`, `sqrt(-1e-400)`, `sqrt(-2e308)`, `ln(-1e400)`, `log(-1e400)`. A double in the same place promotes: `sqrt(-1e299)` is `3.1622776601683796e+149i`.
2. A negative base with a non-integer exponent is `nan`: `(-4)^{0.5}`, `(-2)^{1/3}`, `(-10^{400})^{0.5}`.
3. A complex power carries the `exp(y * log(x))` noise #228 removed from root: `(-4+0i)^{0.5}` is `1.2246467991473532e-16+2i`, `(3+4i)^{2}` is `-6.999999999999997+24i`.
4. `Calculator::root(BigComplex)` at a degree past the double range drops the imaginary part: `(-8+0i)⌄(10^{400})` is `1+0i`, not `1+3.141592653589793e-400i`.

## How these values flow today

`apply` (`eval.cpp`) runs `coerce`, then `promote_complex`, then `coerce` again when the promotion fired, then the kernel. After `coerce` the operands share one arm: an op with a BigReal operand has all of them in BigReal (`coerce`, the `has_big` branch), so `promote_complex` sees either plain reals (Int64 or Double), a Rational the exact arm keeps, or BigReals.

`promote_complex` reads the op's `DomainRule` (`ops.hpp`, `bool (*)(double x, double y)`) and returns early when an operand is a BigReal. The reason is in the test `domain :: a BigReal argument is never domain-checked` (`test_eval.cpp`) and in the comment of `Calculator::log(BigReal, BigReal)`: reading a BigReal as a double turns `10^{-400}` into `0.0` and `10^{400}` into `inf`, and a rule that reads `0.0` (Ln's `x <= 0`) would promote `ln(10^{-400})`. So a BigReal goes to its own kernel, and `Calculator::sqrt(BigReal)`, `root`, `ln` and `log` reject a negative value with Math error.

The Pow row has a range rule and no domain rule, so `Calculator::pow(double, double)` (`std::pow`) and `Calculator::pow(BigReal, BigReal)` (Boost `pow`) run on a negative base and return nan. A Rational exponent goes to `Calculator::pow(Rational)` first, which returns an exact root when there is one (`(-8)^{1/3}` is `-2`) and raises otherwise; the retry in `apply` downcasts to double and calls `promote_complex` again, which has no rule for Pow.

`Calculator::pow(Complex)` is `std::pow` and `Calculator::pow(BigComplex)` is Boost `pow`, both `exp(y * log(x))`. `Calculator::root` on those arms already avoids it (#228): degree 2 is `sqrt`, a degree whose reciprocal is an integer `m` is the exact `pow(x, m)` (binary exponentiation), an integer degree is Newton in BigComplex, the rest is `pow`.

## The fix

### 1. The domain rule reads the operands in their own type

A row's domain rule is written once, as a generic lambda over the real type, and the row stores it instantiated for `double` and for `BigReal`. `promote_complex` picks the instantiation by the arm `coerce` left: Int64 or Double read as double, as today; BigReal reads the BigReal values themselves, so nothing underflows to 0 or overflows to inf. The early return on a BigReal goes.

When the BigReal rule fires, the radicand is lifted with the existing `lift_to_big_complex`, and the existing second `coerce` lifts the rest (its `BigCx` branch). The BigComplex kernels exist for every op that has a domain rule and a BigReal arm (Sqrt, Root, Ln, Log); their values are measured right (findings).

The comparison rules (`x < 0`, `x <= 0`, `std::abs(x) > 1`) read the same for both types. Root's rule asks whether the degree is an odd integer, and so do both real root kernels, each with its own copy: `Calculator::root(double)` through `calc_detail::int_like` and `std::fmod`, `Calculator::root(BigReal)` through `snap_integer`, `floor` and `fmod`, while the rule repeats the double test with `detail::kDomainEpsilon`, a second constant of the same `1e-12` as `calc_detail::kDefaultEpsilon`. The kernels' two tests move into one overloaded `calc_detail::odd_integer` (double and BigReal) in `calc/internal/helpers.hpp`, and the two kernels and the rule call it. `ops.hpp` includes `calc/internal/helpers.hpp` for it (`eval/closed_forms.cpp` already reaches into it), and `kDomainEpsilon` goes: `power_needs_big` reads its exponent with `calc_detail::int_like`, the same value.

Asin, Acos, Acosh and Atanh have rules but no BigReal arm, so a BigReal never reaches their rules (#229).

### 2. A power with a root's exponent is that root

The exact arm already defines a fractional power: `try_rational_pow` (`calc/internal/helpers.hpp`) computes $x^{p/q}$ as the $q$-th root of $x^p$, so `(-8)^{1/3}` is the real `-2`, as `(-8)⌄3` is. The real arms follow the same definition where they return nan today:

- `Calculator::pow(double, double)` and `Calculator::pow(BigReal, BigReal)`: a negative base whose exponent `b` is not an integer and whose `1 / b` is an odd integer `n` is `Calculator::root(x, n)`, the existing real odd root. `(-2)^{1/3}` is `-1.2599210498948732`, the value `(-2)⌄3` gives. Only a negative base with a non-integer exponent reaches this, and every such input is nan today, so no working input changes. Root calls `pow` with a positive base only (`-this->pow(-x, 1 / y)`), so the two cannot call each other in a loop.
- Pow's domain rule: a negative base, an exponent that is not an integer, and a `1 / b` that is not an odd integer. It is Root's rule read on the degree `1 / b`, so the two rules are one function. Each integer test reads the way the kernel behind it reads: "`b` is an integer" is exact in double (`std::pow` returns nan for any non-integer) and `snap_integer` in BigReal, "`1 / b` is an odd integer" is the epsilon or `snap_integer` reading Root uses. The BigReal reading matches the kernel only after step 5. `(-4)^{0.5}` promotes and is `2i`.

A Rational exponent keeps its exact first try, because `promote_complex` does not read a Rational; only when the exact try raises does the retry downcast and meet the rule.

Not covered: a numerator other than 1. `(-8)^{2/3}` is the real `4` from the exact arm, but `(-2)^{2/3}` has no rational root, and after the downcast the exponent is the double `0.666…`, whose `1 / b` is `1.5`. The rule promotes it to the principal complex root `-0.7937005259840998+1.3747296369986026i`; today it is nan. Keeping it real needs the exponent's numerator and denominator to survive the retry, which this branch does not change.

### 3. A complex power with a real exponent takes the root's exact steps

On the Complex and BigComplex arms, `Calculator::pow(x, b)` with a real `b`:

- `b` an integer `m`: the exact integer power root already runs for a degree whose `1 / y` is `m`. On Complex that is `std::pow(x, m)` for a positive `m` with the non-finite fallback, and the BigComplex run for a negative `m`; on BigComplex it is Boost `pow(x, m)` with the same fallback. The step moves out of the two root kernels into one helper per arm, which root and pow both call. This also removes the noise of an integer power, `(3+4i)^{2}`.
- `1 / b` an integer `n`: `Calculator::root(x, n)`.
- otherwise, and for a complex `b`: `pow` as today.

These are the steps `Calculator::root` already takes, reached from the other side; no step is new. Root calls `pow` in two places, and neither may come back: the degree whose reciprocal is an integer runs the integer power directly, not through `pow`; and the last step calls `pow(x, 1 / y)`. For a nonzero radicand that last step is reached only when neither `y` nor `1 / y` is an integer, so `pow` reads `b = 1 / y`, which is not an integer. Its `1 / b` can still come back as one: 325 near-integer degrees such as `7.000000000000001` do (findings). Then `pow` calls `root(x, 7)`, whose integer degree ends in Newton, so the chain stops one step later, at a result one ulp of degree away. A zero radicand skips Newton (`x != 0`) and reaches that last step with an integer `y`: `(0+0i)⌄3` calls `pow(0, 1/3)`, whose `1 / b` is `3`, which would call root again. So the second step of `pow` skips a zero base the same way root skips a zero radicand; `(0+0i)^{0.5}` and `(0+0i)⌄3` are rows (both are `0` today).

### 4. The BigComplex root reads `1 / y` in BigReal

`transcendental.cpp:226` tests `1 / y` for an integer after `static_cast<double>`. It tests the BigReal value instead, so `1e-400` is not `0`. Step 3 needs the same test on BigComplex, so both use one helper.

### 5. A BigReal power snaps its exponent

`(-8)^{9e400/3e400}` is `BigReal("nan")` today. The quotient is 3 at 50 digits and a hair under 3 in the guard digits (`9e400/3e400-3` is `-3e-72`), and `Calculator::pow(BigReal, BigReal)` hands it to Boost `pow` as it is, which sees a non-integer exponent of a negative base. The residue is not the division's alone: `(1e400/3)*3-1e400` is `-1e+328`, so snapping every division would not remove it. The readers that ask for an integer already snap: `trunc`, `floor`, `ceil` and `Calculator::root(BigReal)` (`(-8)⌄(9e400/3e400)` is `-2`). `Calculator::pow(BigReal, BigReal)` joins them and hands Boost `snap_integer(b)`; `snap_integer` leaves a value that is not an integer at 50 digits unchanged, so no other power moves.

## Tests

Test rows are written before the fix and not changed to match it. Expected values are the exact value rounded to the type (mpmath, at least 60 digits).

- `tests/py/e2e/test_eval_e2e.py`, golden table, section "a BigReal outside the real domain": the 15 rows already on the branch, 12 red today and 3 guards (`(-8e399)⌄3`, `ln(10^{-400})`, `sqrt(10^{-400})` stay BigReal) green today.
- The same table gets the power rows: `(-4)^{0.5}`, `(-4)^{-0.5}`, `(-8)^{0.25}`, `(-10^{400})^{0.5}`, `(-2)^{1/3}`, `(-2)^{0.3333333333333333}`, `(-2)^{2/3}`, `(-4+0i)^{0.5}`, `(3+4i)^{2}`, `(1+i)^{2}`, and the guard `(-8)^{1/3}` stays `-2`.
- `test_transcendental.cpp`, the BigComplex root table: `(-8+0i)` at degree `1e400`, expected `1+3.141592653589793e-400i`; and BigComplex pow rows next to it.
- `test_eval.cpp`: `domain :: a BigReal argument is never domain-checked` asserts the bug. It becomes two rows, a negative BigReal promotes to BigComplex and `10^{-400}` does not. The test's reason (a BigReal read as a double underflows) no longer holds once the rule reads the BigReal itself, so the rows keep its guard, `10^{-400}`, and drop the bug.
