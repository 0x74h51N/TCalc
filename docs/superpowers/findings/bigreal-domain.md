# BigReal outside the real domain

## A negative BigReal is a math error (2026-11-11, master be199f5)

`promote_complex` (`eval.cpp`) returns early when any operand is a BigReal, so a BigReal radicand or logarithm argument never reaches the BigComplex arm. `Calculator::sqrt(BigReal)`, `Calculator::root(BigReal)`, `Calculator::ln(BigReal)` and `Calculator::log(BigReal)` then reject the negative value with Math error. The test `domain :: a BigReal argument is never domain-checked` (`test_eval.cpp`) pins this on purpose: its comment says reading a BigReal as a double could underflow to 0 and force a complex op that is not warranted (since 2424521, 2026-07-13).

Math error, through `evaluate_branch`: `sqrt(-1e400)`, `√(-1e400)`, `(-1e400)⌄2`, `\root{-10^{400}}{}`, `(-10^{400})⌄4`, `⌄0.5`, `⌄2.5`, `⌄(-2)`, `sqrt(-1e-400)`, `(-10^{-400})⌄2`, `sqrt(-2e308)` (while `sqrt(-1.7e308)` is a double and works), `ln(-1e400)`, `log(-1e400)`, `log_{2}(-10^{400})`, `(-8)⌄(10^{400})`.

Works: odd integer degrees stay real, `(-10^{400})⌄3` is `-2.154434690031884e+133` and `⌄(-3)` is `-4.641588833612779e-134`. A complex operand already takes the BigComplex arm: `(-10^{400}+0i)⌄2` is `0+1e+200i`, `ln(-1e400+0i)` is `921.0340371976183+3.141592653589793i`.

The BigComplex kernels give the right value for every failing row: the `+0i` forms match mpmath (60 digits, rounded to 16) on sqrt, degrees 2, 4, -2, 0.5, 2.5, ln and log. So the bug is the routing in `promote_complex`, not a kernel.

The underflow worry in that test is real for a rule that reads a double: `10^{-400}` reads as `0.0`, and the Ln rule `x <= 0` would take it. `ln(10^{-400})` and `sqrt(10^{-400})` must stay BigReal (`-921.0340371976183`, `1e-200`); they do today.

## Next to it, not the same cause (2026-11-11, master be199f5)

- `asin`, `acos`, `acosh`, `atanh` have no BigReal or BigComplex arm: `asin(10^{400})` and `asin(10^{400}+0i)` are `unsupported operand type for asin` (#229).

## The power form of a root (2026-11-11, master be199f5)

The `OpId::Pow` row has a range rule and no domain rule, so a negative base with a non-integer exponent is never promoted: `Calculator::pow(double, double)` is `std::pow`, which returns nan. `(-4)^{0.5}`, `(-4)^{1/2}`, `(-4)^{\frac{1}{2}}`, `(-8)^{0.25}`, `(-4)^{-0.5}`, `(-4.5)^{0.5}` are `nan`, and `(-10^{400})^{0.5}` is `BigReal("nan")`. `(-8)^{1/3}` is `-2` from the Rational arm (`try_rational_pow`); `(-2)^{1/3}` has no rational root, falls back to double and is `nan`. `(-8)^{9e400/3e400}` and `(-8e400)^{9e400/3e400}` are `BigReal("nan")`: the exponent is 3 at 50 digits and below it in the guard digits, and Boost `pow` reads all of them; `(-8)⌄(9e400/3e400)` snaps the degree and is `-2`.

A complex base takes `std::pow`, the same `exp(y * log(x))` noise #228 removed from root: `(-4+0i)^{0.5}` is `1.2246467991473532e-16+2i`, `(-1e20+0i)^{0.5}` is `6.123233995736768e-07+10000000000.000004i`, `(-4+0i)^{-0.5}` is `3.061616997868383e-17-0.5i`. Integer exponents too: `(3+4i)^{2}` is `-6.999999999999997+24i`, `(1+i)^{2}` is `1.2246467991473532e-16+2i`.

`1 / (1 / n) == n` in double for every n from 2 to 39 (`python3 -c "print([n for n in range(2,40) if 1/(1/n)!=n])"` prints `[]`). The other way is not safe: 325 non-integers within 40 ulp of an integer from 2 to 1999 have a `1 / (1 / y)` that comes back as that integer, first `7.000000000000001`, `12.999999999999998`, `14.000000000000002`.

## Degree past the double range on BigComplex (2026-11-11, master be199f5)

`(-8+0i)⌄(10^{400})` is `1+0i`; mpmath gives `1+3.141592653589793e-400i`. `Calculator::root(BigComplex)` (`transcendental.cpp:226`) reads `1 / y` through `static_cast<double>`, where `1e-400` is `0`, so `as_int` gives 0 and `pow(x, 0)` returns 1. Boost's `pow(x, 1 / y)` on the same operands gives `(1, 3.1415926535897932385e-400)` (scratch probe). This is the near-integer BigReal degree #228's review raised and its findings called unreachable.

## Designs that delete more, rejected (2026-11-11, master be199f5)

- Drop the domain rules and retry a refused real kernel in complex. The real kernels of `asin`, `acos`, `acosh`, `atanh` (`trig.cpp`) and `pow(double, double)` (`arithmetic.cpp`) return nan instead of refusing, and the kernels also refuse what is not a domain question (degree 0, a zero radicand at a negative degree, log base 1). Telling the two apart needs a new error kind.
- Make root `pow(x, 1 / y)` and keep the exact steps in pow. An integer degree does not survive the double round trip: `1/(1/49)` is not `49`, and 360498 of the integers below 3000000 fail it (`python3 -c "print(sum(1/(1/n)!=n for n in range(1,3_000_000)))"`), so `x⌄49` would lose its exact path.
- Send every non-integer exponent to root as degree `1 / b`. 13893 of 100000 random exponents in `[-10, 10]` do not survive `1/(1/b)`, so a power that works today with such an exponent would move in the last digit.

## Branch review findings (2026-11-11, fix/bigreal-negative-root 9cffdb0 plus uncommitted Task 4)

- A positive integer power on Complex is `std::pow(x, m)` in double (`calc_detail::integer_power`), repeated squaring with a relative error near `m * eps`. `(1.001+0.001i)^{100}` is `1.0996606140809746+0.11022308918546997i`, mpmath `1.0996606140809762+0.11022308918547011i`; `(1.00000001i)^{1000000000}` is `22026.462386386662`, mpmath `22026.463354831518`. Master's `exp(b log a)` was closer there. Root's `1 / y` integer step had the same loss on master; Task 3 brought it to every `^{integer}`. A negative power already runs in BigComplex and matches mpmath.
- `to_big(const Rational &)` (`value.hpp:107`) is `BigReal(r.to_double())`, so a Rational degree lifted next to a BigReal radicand is the double `0.3333333333333333`. `(1e400)⌄(1/3)` is `1.000000000000153e+1200` on master and the branch (exact `1e+1200`); `(-1e400)⌄(1/3)` was a Math error on master and is `-1.000000000000153e+1200-5.231802747013751e+1184i` with Task 4. The exact arm reads a degree `1/3` as the power 3: `(-8)⌄(1/3)` is `-512`.
- Minor: the double `odd_integer` reads with the `1e-12` tolerance, the BigReal one at 50 digits, so `(-8)⌄3.0000000000001` is real `-1.9999999999999538` and `(-1e400)⌄3.0000000000001` is complex.

## Reading the odd root off a double exponent fails (2026-11-12, fix/bigreal-negative-root 88a1b5b)

Task 6 first gave the real kernels `if (a < 0 && !whole(b) && odd_integer(1 / b)) return root(a, round(1 / b))`, with Pow's rule reading the same `1 / b`. `odd_integer(double)` has the 1e-12 tolerance of `int_like`, so it read a near miss as a root: `(-2)^{1.0000000000001}` was `-2.0` and `(-2)^{0.3333333333333}` was `-1.2599210498948732`, both real where the principal value is complex. Dropping the tolerance does not save it: `1/(1/3)` is `3.0` but `1/(1/49)` is `49.00000000000001`. The double cannot tell `1/3` from a decimal near it; the exponent's denominator can, so the decision moved before the exponent leaves its fraction (`Trait::RootExponent` in `apply`). No complex code was removed: in a complex number set (#230) skipping that rewrite gives the principal value through the existing complex power.
