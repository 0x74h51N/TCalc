# A power from its exact fractional exponent

Milestone: none yet (#231 has none; proposed: First release). Issue: #231. Measurements: [fractional-exponent.md](../findings/fractional-exponent.md). The correctly rounded path is the multiprecision mode of #275, not this spec.

## The bug

When the exact kernel refuses a power, the retry casts the exact exponent `p/q` to its nearest double before the power is taken. The result is off by about `|ln r| / 2` ulps for a result r (findings), whatever the sign of the base: a positive base loses digits as much as the negative one #231 names, and `Root` and `Pow10` take the same cast. A negative base at an even q also comes back with a nonzero part where the exact part is `0`, and a root degree past `2^53` loses its parity on the same cast.

## The line

The result is within 1 ulp of the exact value, part by part, and a part that is exactly `0` is `0`. This is #275's default line; the correctly rounded double is #275's mode.

## Cases

Every case was measured e2e (editor plain text, `tokenize`, `evaluate_branch`) on this branch at `e076950` and again at `c85296e` (#249 merged), native module rebuilt, with the same values. Expected is mpmath at 80 digits rounded to double, part by part. Fix is the algorithm below run on the row in a C++ probe (`p231/final.cpp`, findings), with its ulps against Expected. Each row becomes a test row that allows 1 ulp per part and a zero part only as `0`; a row whose Today is more than 1 ulp off is red before the fix.

Negative base, even q:

| Input | Expected | Today | Fix, ulps |
|---|---|---|---|
| (-2)^(1.0000000000001) | -2.0000000000001386 - 6.283185307180022e-13 i | -2.0000000000001386 - 6.276972133682025e-13 i | 0, 1 |
| (-2)^(0.5000000000001) | -4.4428829381586743e-13 + 1.414213562373193 i | -4.442495702019156e-13 + 1.414213562373193 i | 0, 0 |
| (-2)^(1.1) | -2.0386342710747227 - 0.6623924280875912 i | -2.0386342710747223 - 0.6623924280875919 i | 1, 0 |
| (-2)^(2.9999999999999) | -7.999999999999446 + 2.5132741228716605e-12 i | -7.999999999999444 + 2.5182604369085336e-12 i | 0, 0 |
| (-2)^(3/2) | 0 - 2.8284271247461903 i | -5.195736337412959e-16 - 2.82842712474619 i | 0, 0 |
| (-1/2)^(3/2) | 0 - 0.3535533905932738 i | -6.4946704217662e-17 - 0.3535533905932738 i | 0, 0 |
| (-2)^(7/4) | 2.378414230005442 - 2.378414230005442 i | 2.3784142300054416 - 2.3784142300054425 i | 0, 0 |
| (-8)^(5/6) | -4.898979485566356 + 2.8284271247461903 i | -4.898979485566357 + 2.82842712474619 i | 0, 0 |
| (-10)^(301/2) | 0 + 3.1622776601683793e+150 i | 9.76050667268958e+136 + 3.1622776601685065e+150 i | 0, 0 |
| (-3)^(609803/1058) | 3.8745589136552445e+274 + 9.2182330420805e+274 i | 3.874558913655538e+274 + 9.218233042081586e+274 i | 1, 1 |
| (-2)^(0.3333333333333) | 0.6299605249475363 + 1.0911236359716303 i | same | 0, 0 |
| (-2)^(0.5) | 0 + 1.4142135623730951 i | same | 0, 0 |
| (-4)^(1/2) | 0 + 2 i | same | 0, 0 |
| (-1)^(1/2) | 0 + 1 i | same | 0, 0 |
| (-3)^(1/4) | 0.9306048591020996 + 0.9306048591020996 i | same | 0, 0 |
| (-2)^(1/4) | 0.8408964152537145 + 0.8408964152537145 i | same | 0, 0 |
| (-9223372036854775807-1)^(1/2) | 0 + 3037000499.97605 i | same | 0, 0 |

Positive base, and the same power written as a root or a power of ten:

| Input | Expected | Today | Fix, ulps |
|---|---|---|---|
| 17^(8711/674) | 7993386127887876 | 7993386127887863 | 0 |
| (17)⌄(674/8711) | 7993386127887876 | 7993386127887863 | 0 |
| 17^(-8711/674) | 1.251034272585846e-16 | 1.251034272585848e-16 | 0 |
| (1/2)^(8711/674) | 0.00012864363123970833 | 0.00012864363123970835 | 1 |
| (38/3)^(20993/82) | 1.9724528358173784e+282 | 1.9724528358172995e+282 | 1 |
| 29^(9973/1000) | 384145042658027.44 | 384145042658028.44 | 0 |
| 2^(1000001/1000) | 1.0722515778205376e+301 | 1.07225157782052e+301 | 0 |
| 7^(3001/10) | 4.110757031007188e+253 | 4.11075703100737e+253 | 1 |
| 10^(331897/1242) | 1.6898894438436359e+267 | 1.6898894438437454e+267 | 1 |
| 11^(1005956/3671) | 2.3470978086479803e+285 | 2.3470978086480007e+285 | 0 |
| 10^(185396/641) | 1.6956225092842887e+289 | 1.6956225092843623e+289 | 1 |
| 27^(720892/4087) | 2.9742381884890863e+252 | 2.9742381884892104e+252 | 1 |
| 20^(39129/1157) | 1.0000053740448948e+44 | 1.0000053740448944e+44 | 0 |
| 10^(22/7) | 1389.4954943731377 | 1389.4954943731375 | 0 |
| ⏨(22/7) | 1389.4954943731377 | 1389.4954943731375 | 0 |
| ⏨(331897/1242) | 1.6898894438436359e+267 | 1.6898894438437454e+267 | 1 |
| 27^(41/3) | 3.647299637717079e+19 | 3.6472996377170715e+19 | 1 |
| 3^(1/3) | 1.4422495703074083 | same | 0 |
| 2^(1/10) | 1.0717734625362931 | same | 0 |
| ⏨(-1/2) | 0.31622776601683794 | same | 0 |
| (17)⌄(3) | 2.571281590658235 | same | 0 |
| 9223372036854775807⌄3 | 2097152 | same | 0 |
| 109889063671⌄3 | 4789.80858033901 | same | 0 |
| (-10)⌄5 | -1.5848931924611134 | -1.5848931924611136 | 1 |
| (-4)⌄2 | 0 + 2 i | same | 0, 0 |
| (3037000500)⌄(1/2) | 9.22337203700025e+18 | same | not this path |
| 3037000500^2 | 9.22337203700025e+18, BigReal | same | not this path |
| ⏨(19) | 1e+19, BigReal | same | not this path |

`(-10)⌄5` is the existing row `root-fifth-minus-ten` at 1 ulp, and it stays there. `(-4)⌄2` is the existing `root-domain-complex`. `3037000500^2` and `⏨(19)` have a whole exponent, and `power_retry_arm` keeps them BigReal. `(3037000500)⌄(1/2)` is a `Root`, which has no retry rule: it reaches the exact retry with the whole exponent 2 and stays a double.

Odd q past `2^53`, and a brute sum over such terms:

| Input | Expected | Today | Fix, ulps |
|---|---|---|---|
| (-2)^(1/9007199254740993) | -1 | 1 + 3.487868498008632e-16 i | 0 |
| (-2)⌄(9007199254740993) | -1 | 1 + 3.487868498008632e-16 i | 0 |
| (-2)^(-1/9007199254740993) | -0.9999999999999999 | 0.9999999999999999 + 3.4878684980086313e-16 i | 0 |
| (-2)^(1/9007199254740991) | -1 | same | 0 |
| (-9223372036854775807-1)⌄(9223372036854775807) | -1 | 1 + 3.4061215800865545e-19 i | 0 |
| \sum_{n=1}^{10} (-2)^{1+n/10000000000000} | -20.000000000007624 - 3.455751918950449e-11 i | -20.00000000000762 - 3.455479666011094e-11 i | |

The sum row compares each part against its own size, within `1e-14`: today's imaginary part is `8e-5` of itself off, so the row is red before the fix.

Errors: `(5)⌄(0)` reaches the retry and stays a math error. `0^(-1/2)` and `0⌄(-2)` are taken to BigReal by `power_needs_big` (`log10(0)`) before the kernel and do not reach it; they stay rows, as math errors. A degree of `-9223372036854775807-1` has no reciprocal in int64: `(2)⌄(-9223372036854775807-1)` is `1.0` and `(-1)⌄(-9223372036854775807-1)` is `1 - 3.4061215800865545e-19 i` since #249, and both stay so; they are rows.

## How a fractional power runs today

`apply` (`eval.cpp`) lifts integer operands to `Rational`. A negative base with an odd q is taken by the real-first rewrite before dispatch: `Pow(x, p)`, then `Root(power, q)`. Anything else reaches the exact kernel, `Calculator::pow(const Rational &, const Rational &)` (`arithmetic.cpp`), `Calculator::root` or `Pow10`'s `pow(10, a)`, which return the exact power or throw (`try_rational_pow`). The catch asks the row's retry rule, `RetryArmRule` (`ops.hpp`): `power_retry_arm` gives `Pow` and `Pow10` a BigReal retry for a whole exponent and a double retry for any other, and `Root` has no rule, which is a double retry too. So every operand is cast with `as_double`, the domain rule promotes a negative base to `Complex`, and `std::pow` runs on the rounded exponent. glibc `pow` is at most 1 ulp from the exact power of the double it is given (findings); the cast is where the digits go. `Root`'s degree `9007199254740993` is cast the same way, to the even `9007199254740992`, before the domain rule reads its parity.

## The fix

1. **The hook.** The closest existing code is the row's retry rule, `RetryArmRule`. It returns an `Arm`, and the catch then casts every operand to that arm; the cast is the loss, so an `Arm` cannot carry `p/q`. The row gets a second retry field beside it, an exact retry that receives the refused `Rational` operands and returns the value. The catch reads the arm rule first, as today; where it would cast to double and the row has an exact retry, it calls that instead. So for `Pow` and `Pow10` a whole exponent is still decided by `power_retry_arm`; `Root` has no rule, and every refused root reaches the exact retry. Three rows set it, each with the exponent it means: `Pow` with `(x, y)`, `Root` with `(x, 1/y)`, `Pow10` with `(10, a)`. `Root`'s row forms `1/y` as `Rational(den, num)`; at the degree `-9223372036854775807-1`, whose reciprocal is past int64 (`(2)⌄(-9223372036854775807-1)`), the exact retry gives no value (the int256 reciprocal of the real-first rewrite costs 175 ns a call, +10 % on a refused root, findings) and the catch casts to double as today, so #249's results stay. It raises the zero degree's math error before it forms `1/y` (`(5)⌄(0)`: `boost::rational(1, 0)` would throw `bad_rational`, not a `CalculatorError`).
2. **One function, two results.** The three rows share one function over the base `a/c` and the exponent `p/q`. A positive base, or a negative base at an odd q, gives a real `double`: the magnitude, negated for a negative base at an odd p. A negative base at an even q gives a `Complex`. The choice is made once, in the shared function, from the exact `q`; the rows only say which operands are base and exponent. Since `Root` reaches it with the degree exact, `(-2)⌄(9007199254740993)` is the real root `-1`; the domain rule never sees a cast degree. A real power with `p = 1` and a `q` that is an exact double is a root at an integer degree: it goes to #271's kernel, `Calculator::root(double, double)`, with the signed base as a double, so it keeps #271's correctly rounded result. Without it `109889063671⌄3` is `4789.8085803390095`, 1 ulp off where #271 gives `4789.80858033901`, and over 6000 random roots the correctly rounded ones fall from 5825 to 4860 (review, findings). A degree past `2^53` is no exact double and takes the corrected pow, which keeps its parity.
3. **The corrected pow.** `x = |a|/c` and `e = p/q` rounded to double, `r = pow(x, e)`. Their own roundings are exact residuals by `fma`: `dx = fma(-x, c, |a|) / c` and `de = fma(-e, q, p) / q`. The magnitude is `r * exp(de * ln x + e * log1p(dx / x))`, taken as `fma(r, expm1(t), r)` for that sum t. `expm1` and `log1p` keep a base near 1 at a large exponent right, where a first-order correction left 936 of 16759 powers 9 ulps or more off (findings). For an integer or a dyadic base `dx` is `0`, with no branch.
4. **Angle.** `pi * p / q`, folded to its quadrant and the nearer quadrant edge exactly in integers, the fold `Calculator::real_half_turns` does today, then `sinl` and `cosl` of the small residual. The fold moves out of `real_half_turns` into a helper over the floating type that both use, not written twice, with `real_half_turns`' results unchanged (it gives `-0.0` on some edges today, and `closed_forms.cpp` reads it). An angle on a quadrant edge gives an exact `0` and an exact `1`; `principal_power` makes a zero part `+0`, so no part shows as `-0` (`(-4)^(1/2)`). The magnitude is kept in `long double` (`r + r * expm1(t)`) and multiplied by `cosl` and `sinl` there, and each part is rounded to double once: with the product in double, 834 of 13253 negative-base powers had a part 2 or 3 ulps off; in `long double`, none past 1 (findings).

No other branch is added: the real-first rewrite, the domain rule, the range rule and `power_retry_arm` are untouched, and there is no midpoint check and no BigReal fallback.

Cost (findings, `-O2 -march=native`, not Release): a real power 29 to 31 ns, a complex one 89 ns, against `std::pow`'s 12 to 16 ns. A refused power costs 1.8 to 2.1 us in Release today, nearly all of it the exception the exact kernel throws, which stays: about +1 % for a real power and +4 % for a complex one. The plan measures it in Release, before and after.

## What the user sees

Every row of the tables is within 1 ulp of its Expected column, part by part, and its zero parts are `0`; the errors stay errors. The type does not change: a positive base stays a double, a negative base at an even q stays a `Complex`, nothing turns into BigReal or BigComplex. A root at an integer degree with exact operands, such as `9223372036854775807⌄3`, reaches #271's kernel through this retry and keeps its result; a root of double operands, such as `(1e300)⌄3`, keeps it directly.

## Not in this spec

- The correctly rounded double, and the digits a double cannot hold: #275.
- An operand past `2^53` (a numerator or denominator of the base or the exponent). `9223372036854775807⌄3` and `9007199254740993⌄2` are still right, but a base near 1 at such an exponent is not: `(999999999999999999/1000000000000000000)^(1000000000000000001/2)` rounds its base to `1` and stays `1` (exact `0.6065306597126334`); `(9007199254740992/9007199254740991)^((-9223372036854775807-1)/3)` is 378 ulps off, though every operand is an exact double, because the correction exponent t is large; `(9007199254740992/9007199254740991)^(4611686018427387904/3)` comes out `0` and `promote_range` widens it to BigReal (review, findings). Today all of them are wrong by far more. They are #275's.
- #263: `27^(41/3)` has the exact answer `36472996377170786403`, past int64. Here it is within 1 ulp of it; the exact BigReal integer is #263's fix.
- A power whose result passes double's range is taken by `power_needs_big` before the kernel and runs in BigReal or BigComplex: #274 for the nonzero part of `(-1000)^(307/2)`.
- A root near 1 that collapses to `1.0` (`(0.5)⌄(9223372036854775807)`): #249 and #275.
- A base or exponent that is already a double (a computed value such as `sin(1)`): it has no exact `p/q` to read.
