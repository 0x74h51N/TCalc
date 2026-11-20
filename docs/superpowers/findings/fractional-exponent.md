# Fractional exponent

## The path today (2026-11-19, master 69a8fd8)

`(-2)^1.0000000000001`: the exponent is `Rational(10000000000001, 10000000000000)`; its denominator is even, so the real-first rewrite (`RootExponent`, `eval.cpp`) does not take it, the Rational pow refuses (no exact root), the retry is double (`power_retry_arm`: not a whole exponent), the domain rule promotes to complex, and `std::pow` runs on the rounded exponent. Measured e2e: `-2.0000000000001386 - 6.276972133682025e-13 i` (exact imaginary part `-6.283185307180022e-13`).

## Loss in iterated sums (2026-11-19)

Brute sums against mpmath at 60 digits with TCalc's own rule (an odd reduced denominator takes the real root, an even one the principal power), probe `sum231.py` (scratch). Each part's error against its own size:

- `\sum_{n=1}^{N} (-2)^{1+n/10000000000000}`: imaginary part `7.9e-05` at N 10, `7.7e-06` at 100, `7.7e-07` at 1000; real part `2e-16`. The loss is per term, from the rounded exponent, and does not grow with N.
- `\sum_{n=1}^{N} (-2)^{n/10}`: `4.4e-17` at 10, `4.9e-15` at 100, `1.1e-14` at 1000.
- `\sum_{n=1}^{N} (-3)^{n/7+1/2}`: up to `7.6e-14` at 1000.
- Times: 0.8 ms at 10 terms, 5.5 ms at 100, 54 to 98 ms at 1000.

A first run with the principal power on every term showed a relative error of `0.46`: that was the reference ignoring the real-first rule, not TCalc.

## Cost of BigComplex (option B) (2026-11-19)

`calc_native.apply(Pow, ...)`, mean of 2000 calls with Python overhead: complex double 7.8 us, today's Rational path 26.7 us, BigComplex base with BigReal exponent 82.8 us (`1.0000000000001`) and 158.7 us (`1.1`). The BigComplex results are right (`-2.000000000000139 - 6.283185307180022e-13 i`).

## The angle from the exact exponent (2026-11-19)

`(-b)^(p/q)` = `b^(p/q) * (cos(pi p/q) + i sin(pi p/q))`, with the angle reduced exactly in the Rational to the nearest quarter turn before sin and cos see a double. Python prototype in double: `1.0000000000001`, `0.5000000000001`, `0.3333333333333` (imaginary), `1/2`, `7/4`, `2.9999999999999` and `1/9007199254740993` exact or within 1 ulp; `1.1` 1 ulp on both parts. `Calculator::real_half_turns(TrigFn, const Rational &)` (`trig.cpp:206`) already computes sin and cos of pi times an exact Rational this way, with an int256 fold past int64.

## The exact angle in native, and where the error really is (2026-11-19, master 69a8fd8)

Probe `p231/sweep2.cpp` links `libcalc_core.a`: 13253 random `(-b)^(p/q)`, b 2 to 31, even q up to 10000, graded in ulps against mpmath (`p231/grade.py`), the worse part of each result.

- Today (`apply(Pow, {-b, p/q})`): 968 rows exact, 3890 rows 9 ulp or more.
- Magnitude from today's positive power (`apply(Pow, {b, p/q})`) times `exact_half_turns` / `real_half_turns`: 2481 exact, 568 rows 9 ulp or more. The magnitude alone is 9 ulp or more on 496 rows: the angle is fixed, the magnitude is not.
- Magnitude `powl(b, (long double)p / q)` rounded to double, angle in double: at most 3 ulp, 5 rows at 3.
- Magnitude, angle fold and product all in long double, one rounding to double: 13223 exact, 30 rows 1 ulp.

Cost per call (200000 calls, `(-2)^(11/10)`): today's apply 6.3 us, the positive magnitude apply 9.9 us (its exact kernel tries an integer 10th root of 2048 and throws), sin and cos by half turns 145 ns, bare `std::pow` on complex 1.5 ns. The exception is the cost, not the arithmetic.

## A positive base loses digits too (2026-11-19, master 69a8fd8)

The retry casts the exact exponent to double for a positive base as well, and `std::pow` reads the rounded exponent. e2e (`e2e_any.py`) against mpmath rounded to double:

- `17^(8711/674)`: `7993386127887863`, correctly rounded `7993386127887876`.
- `29^(9973/1000)`: `384145042658028.44`, correctly rounded `384145042658027.44`.
- `2^(1000001/1000)`: `1.07225157782052e+301`, correctly rounded `1.0722515778205376e+301`.
- `7^(3001/10)`: `4.11075703100737e+253`, correctly rounded `4.110757031007188e+253`.
- `10^(22/7)`: `1389.4954943731375`, correctly rounded `1389.4954943731377`.
- `3^(1/3)`, `2^(1/10)`: correct.

No issue covers this: #263 is the exact result past int64, #231 the negative base.

## Zero parts that are not zero today (2026-11-19, master 69a8fd8)

A half-integer exponent has an exact zero real part, and today's `std::pow` leaves noise there: `(-2)^(3/2)` is `-5.195736337412959e-16 - 2.82842712474619 i` (exact `-2.8284271247461903 i`), `(-10)^(301/2)` has a real part `9.76050667268958e+136`, `(-1000)^(307/2)` (BigComplex) `-4.234080055950928e+412`. The exact angle gives these a real part of exactly 0.

## Where the digits go (2026-11-19, master e076950)

The exponent `p/q` reaches `std::pow` as the nearest double `e(1 + d)`, `|d|` up to `2^-53`. The result is then `x^e * x^(e d)`, a relative error of `e ln(x) d`: about `|ln r| / 2` ulps for a result r. `17^(8711/674)` has `ln r` near 36.6, and is 13 ulps off; a result near `1e301` has `ln r` near 693. `std::pow` itself is not the loss: over 5000 random `b^e` (probe `p231/powcheck.cpp`, b 2 to 31), glibc `pow` is at most 1 ulp from the exact power of the double e it is given, and correctly rounded on all but 3.

## A long double fast path with a midpoint check (2026-11-19, master e076950)

Probe `p231/ziv.cpp`, 19979 random `b^(p/q)` and `(-b)^(p/q)`, b 2 to 31, q up to 10000, graded against mpmath. Magnitude `powl(b, (long double)p / q)`; angle from the `real_half_turns` fold in long double; real and imaginary parts as `m * cos` and `m * sin` in long double, each rounded to double once. Error bound: `(|ln m| / 2 + 4)` long double ulps of m for the magnitude, twice that plus 4 ulps of m for a part. A result within the bound of the midpoint of two doubles is flagged.

- Magnitude: 34 rounded wrong, all 34 flagged, 160 flagged in all (0.8 %).
- Real part: 17 wrong, all flagged, 1295 flagged (6.5 %). Imaginary part: 25 wrong, all flagged, 1320 flagged (6.6 %).
- Every unflagged result is the correctly rounded one.

Cost (`p231/cost.cpp`, `2^(11/10)`): the long double path with sin and cos 212 ns; the BigReal magnitude 6.8 us; BigReal magnitude with BigReal sin and cos 24.8 us. Today's `apply` is 6.3 us, nearly all of it the exception the exact kernel throws.

On arm64 macOS `long double` is `double` (`complex-root.md`): the bound is then 2048 times wider and most results take the BigReal path. Not measured on macOS.

## The parity past 2^53 (2026-11-19, master e076950)

`(-2)^(1/9007199254740993)`: the real-first rewrite (`apply`, `eval.cpp`) hands `Root` the radicand `-2` and the degree as an int64; the exact kernel refuses, `Root` has no retry arm, so the retry casts the degree to double, `9007199254740992`, even, and the domain rule promotes to complex: `1 + 3.487868498008632e-16 i`. At `9007199254740991` the cast is exact and odd: `-1.0`. The real root is `-(1 + 7.7e-17)`, `-1.0` in double.

## A BigComplex power with a zero part (2026-11-19, master e076950)

`(-1000)^(307/2)` passes `power_needs_big` before the kernel, so it runs as Boost's BigComplex `pow`, `exp(y log x)`, with an exact exponent `153.5`: `-4.234080055950928e+412 - 3.162277660168379e+460 i`, exact real part `0`. The error is 1e-48 of the modulus, from `exp(log)`, not from a rounded exponent.

## The first bound misses wrong results near the top of the range (2026-11-19, review)

The bound `(|ln m| / 2 + 4)` long double ulps above was measured, not argued, and it is wrong: `(long double)p / q` is off by up to `2^-64` relative, which moves m by up to `|ln m| * 2^-64` relative, `|ln m|` long double ulps at the bottom of a binade. Probe `p231/bound.cpp`, 28978 powers, half of them `1e250` to `1e307`: the error reaches 1.88 times that bound, and 49 of the 2071 wrong magnitudes are not flagged, among them `10^(331897/1242)` (long double path `1.6898894438436361e+267`, correct `1.6898894438436359e+267`), `11^(1005956/3671)`, `10^(185396/641)`, `27^(720892/4087)`. The argued bound `|ln m| * 2^-64 * m + 2` ulps flags every wrong one (error at most 0.98 of it) but flags 44 % of those powers: near `1e300`, `|ln m|` is 690 of the 2048 long double ulps in one double ulp. glibc `powl` on its own long double input is at most 0.92 long double ulps off on these rows.

## The integer part split off (2026-11-19, master e076950)

`m = b^n * b^(r/q)`, `n = floor(p/q)`, `0 <= r < q`, both factors by `powl`, product in long double. The exponent `r/q` is below 1, so its rounding moves m by at most `ln b * 2^-64` relative, whatever m is. Probe `p231/split.cpp`, 28965 powers, half of them `1e250` to `1e307`, against mpmath: 14 magnitudes rounded wrong (2071 without the split), every one flagged by the relative bound `2 * (3 + ln b) * 2^-64` (two `powl`, the exponent, the product), the error at most 0.33 of it; 0.83 % of magnitudes flagged. The parts, with `6 * 2^-64` more for the angle fold, `sinl` and `cosl`: 12 and 5 wrong, all flagged, at most 0.30 of the bound, 1.2 % and 1.3 % flagged. 326 ns per power with both parts.

## Root and Pow10 take the same cast (2026-11-19, master e076950)

`(17)⌄(674/8711)` is `7993386127887863`, as `17^(8711/674)`; `⏨(22/7)` is `1389.4954943731375`, as `10^(22/7)`. `Root` has no retry rule, so a refused exact kernel retries in double; `Pow10` has `power_retry_arm` on its argument (`ops.hpp`), which also retries a non-whole one in double, while `⏨(19)` is `BigReal 1e+19`. `(-2)⌄(9007199254740993)` typed directly is `1 + 3.487868498008632e-16 i`: the degree is cast to the even `9007199254740992` before the Root domain rule reads its parity. `(-2)^(-1/9007199254740993)` is `0.9999999999999999 + 3.4878684980086313e-16 i`, real root `-0.9999999999999999`.

## A base long double cannot hold, and a base below e^-3 (2026-11-19, second review)

The split's bound has no term for the base itself. `|x| = a/c` rounded to long double is off by up to `2^-64` relative, and the exponent multiplies that: `|p/q| * dx` more, with `dx` the base's own relative rounding (0 for an integer or a dyadic base). Probe `rev2/fast.cpp` and `rev2/grade.py`, 4485 non-dyadic rational bases: 107 magnitudes rounded wrong and not flagged, up to 4448 times the bound. `(38/3)^(20993/82)`: fast path `1.9724528358173787e+282`, correct `1.9724528358173784e+282`, today `1.9724528358172995e+282`. `(999999999999999999/1000000000000000000)^(1000000000000000001/2)`: fast path `0.6139198003931642`, correct `0.6065306597126334`, today `1.0`, since the base is `1.0` as a double.

The bound also read `ln|x|`, negative below `e^-3`: for `(1/32)^(p/q)` nothing was ever flagged. With `|ln|x||` and the `|p/q| * dx` term, 8000 dyadic bases, 4000 subnormal results, 457 angles near a quadrant edge with even q up to `2^63` and 300 rows with p near int64's max are at most 0.36 of the bound, with no unflagged wrong part.

`powl` with an integer n up to `9e18`, 3000 exact inputs (`rev2/pown.cpp`): at most 0.79 long double ulps. glibc publishes measured ulps, not a guarantee.

## Which errors reach the retry (2026-11-19, second review)

`0^(-1/2)` and `0⌄(-2)` never reach it: `power_needs_big` reads `log10(0)`, `-inf`, and sends them to BigReal first (probe `rev2/err.cpp`). `(5)⌄(0)` does: the exact kernel's `require_nonzero` throws, and the retry runs; `1/y` there would build `boost::rational(1, 0)`, which throws `bad_rational`, not a `CalculatorError`.

## The corrected double pow (2026-11-20, master e076950)

`r = pow(x, e)` on the rounded exponent `e`, then `y = fma(r, d * log(x), r)` with `d = fma(-e, q, p) / q`, the exponent's own rounding (exact for p and q below `2^53`): `x^(p/q) = x^e * x^d`. Probe `p231/corr.cpp`, 28961 integer-base powers, half of them `1e250` to `1e307`: at most 1 ulp, 76 % correctly rounded (today 92 % are 9 ulps or more). 18.2 ns with a hardware `fma` (`-march=native`), against 12.3 ns for today's `std::pow`. With `fmal` in long double for the residual it is 227 ns: x86-64 long double `fma` is a software routine.

## Release timing (2026-11-20, plan review)

The repository build is Debug (`src/native/build/native/CMakeCache.txt`), and the 6.3 us above is Debug. In Release a refused `apply` costs 1.8 to 2.1 us today (`Pow(-2, 11/10)` 2.08 us, `17^(8711/674)` 1.81 us, `Root(12, 2)` 1.96 us). The powl split adds 450 to 650 ns there (+25 to 35 %): each `powl` is about 215 ns, `fmal` about 200 ns.

## A rounding side read from logarithms: failed (2026-11-20)

On top of the corrected pow, `L = (p/q) logl(x)` against `logl` of the midpoint toward the true value decides the side. Probe `p231/side.cpp`: 90 ns, no wrong result unflagged, but 86 % flagged: near `1e300`, `|L|` is 690 and its `2^-63` rounding is wider than the `2^-54` between a double and its midpoint. A log comparison cannot tell the side for a large result.

## Double-double integer power and a long double fraction (2026-11-20)

`x^n` by repeated squaring in double-double (`fma` products), `x^(r/q) = expl((r/q) logl x)`, the product (or, for a negative n, the quotient) in long double; flagged within `(ln x + 6) * 2^-63` relative of a midpoint. Probe `p231/dd.cpp`, the same 28961 powers: 116 ns, 14 wrong, all flagged, 1.14 % flagged in all. A first version that took the reciprocal in double-double missed 2 rows at `n = -206`: its low part fell into subnormals near `1e-307`. Integer bases only; a non-dyadic base and the angle are not in this probe.

## The corrected pow on a negative base at an even q (2026-11-20)

Magnitude by the corrected pow, angle by the half-turn fold, 13253 negative-base powers (base 2 to 31, even q up to 10000, results inside double's range). Probe `p231/cparts.cpp`, the magnitude rounded to double and multiplied by `cos` and `sin` in double: worse part 0 ulp 4159, 1 ulp 8260, 2 ulps 808, 3 ulps 26. Probe `p231/cparts2.cpp`, the corrected magnitude kept in long double (`r + r*c`), the angle in long double, each part rounded once: 0 ulp 7649, 1 ulp 5604, never 2. 82 ns a call (`-O2 -march=native`). A part the angle makes exactly 0 stays 0.

## The corrected pow with the base's rounding (2026-11-20)

For a base `a/c` and an exponent `p/q`, all four exact doubles: `x = RN(a/c)`, `dx = fma(-x, c, a) / c`, `e = RN(p/q)`, `de = fma(-e, q, p) / q` (both residuals exact), `y = fma(r, expm1(de * log(x) + e * log1p(dx / x)), r)` with `r = pow(x, e)`. Probe `p231/basecorr.cpp`, 16759 powers (non-dyadic bases such as `38/3`, and bases near 1 with exponents up to `1e12`): today 15222 of them 9 ulps or more; first-order correction without `expm1`/`log1p` 936 still 9 or more (a base near 1 at a large exponent); with them 0 ulp 12535, 1 ulp 4224, never 2. 28.0 ns against `pow`'s 15.6 ns. An operand that is not an exact double (int64 past `2^53` that is no power of two) has no exact residual: `(999999999999999999/1000000000000000000)^(1000000000000000001/2)` rounds its base to `1`.

## The spec's algorithm on the spec's rows (2026-11-20)

Probe `p231/final.cpp`: the corrected pow with the base and exponent residuals, a negative base at an even q in long double with the half-turn fold, each part rounded once. On the 41 rows of the spec (`p231/rows.txt`), every part within 1 ulp of mpmath at 80 digits, zero parts `0`; the fold gave `-0.0` for a real part on the imaginary axis (`(-4)^(1/2)`), so the spec asks for `+0`. 29 to 31 ns a real power, 89 ns a complex one (`-O2 -march=native`).

## Spec review 4 (2026-11-20)

Probes in `rev4/`. `fuzz.py` seeds 1 to 3, 71958 rows (integer and non-dyadic bases up to `2^53`, bases near 1, negative bases at even q near quadrant edges with q up to `2^53`, odd q, results subnormal to `1e308`): none past 1 ulp, no nonzero exact-zero part, about 78 % at 0 ulp. `big2.py`, p a power of two from `2^54` to `2^62`, base near 1: 218 of 1226 past 1 ulp, 87 past 9 (`(9007199254740992/9007199254740991)^((-9223372036854775807-1)/3)` 378 ulps; at `4611686018427387904/3` the result is `0` and `promote_range` makes it BigReal); q, a or c a power of two past `2^53`: 3000 rows, none past 1 ulp. `rootcmp.py`, 6000 roots `a⌄n` at n 2 to 20: today 5825 correctly rounded and 168 at 1 ulp, through the corrected pow 4860 and 1133 (`109889063671⌄3` today `4789.80858033901`, corrected pow `4789.8085803390095`). A prototype of the exact retry in the catch: native 13094 passed, `test_eval_e2e.py` 535, `test_reductions_e2e.py` 50; of 41 refused powers the suites reach, 9 change value, all toward mpmath.

## Release cost of the exact retry (2026-11-20, branch on c85296e)

`calc_core` built Release in scratch build dirs for `c85296e` and the branch; probe `perf/apply_cost.cpp`, `apply` 200000 calls, best of 3, two runs each. Pow: `Pow(-2, 11/10)` 1926 to 1950 ns before, 1945 to 1958 after; `Pow(17, 8711/674)` 1846 to 1869, 1892 to 1903; `Pow(38/3, 20993/82)` 1859 to 1870, 1899 to 1936 (+0.4 to 4 %). Root: `Root(12, 2)` 2129 to 2200, 2355 to 2368; `Root(17, 6)` 2090 to 2130, 2299 to 2301 (+8 to 10 %). The Root cost is its reciprocal through `calc_detail::narrow` of an int256 quotient: 175 ns a call (`perf/inv_cost.cpp`), against 0.4 ns for `Rational(den, num)`.

After Root's reciprocal became `Rational(den, num)` with int64 min declined (2026-11-20), five interleaved runs each, min and median: `Pow(-2, 11/10)` -0.8 % and -2.9 %, `Pow(17, 8711/674)` +1.8 % and +0.1 %, `Pow(38/3, 20993/82)` +2.3 % and -0.6 %, `Root(12, 2)` +0.6 % and +1.6 %, `Root(17, 6)` +1.9 % and +1.4 %; the run to run spread is a few percent.

## Where a refused power's 2 µs goes (2026-11-20, branch, Release)

Probe `perf/split.cpp` against the Release `calc_core`, best of 3 over 200000 calls, for `17^(8711/674)`. The `apply` total is about 1920 ns, the same on master. `Calculator::pow(Rational, Rational)` refusing, with its throw and catch: 1376 ns. An empty `throw std::runtime_error` and catch: 746 ns. `real_power`: 31 ns. The corrected pow is under 2 % of the call. Reading the 630 ns gap as the exact search is false: `perf/exact_split.cpp` times `try_rational_pow` alone at 11.1 ns for `17^(8711/674)`, 12.3 ns for `(38/3)^(20993/82)`, 7.5 ns for `(-2)^(11/10)`, 11.1 ns for `17^(1/6)`, 59.6 ns for `12^(1/2)` (Boost integer sqrt) and 413.6 ns for `123456789012^(1/3)` (cpp_int Newton, 407.7 ns of it). So the refusal's throw of `CalculatorError` costs about 1360 ns on its own, nearly double the empty `std::runtime_error`, and the search matters only for a large int64 radicand at q >= 3.

## Operands that lose digits as doubles (2026-11-20, #277, feat/power-cast-loss-error on 1598c36)

`corrected_pow` reads the rounded operands, so a digit the int64 to double cast dropped is gone: on master 1598c36 `(999999999999999999/1000000000000000000)^(1000000000000000001/2)` is `1.0` (exact `0.6065306597126334`) and `(9223372036854775807/9223372036854775806)^(9223372036854775805/2)` is `1.0` (exact `1.6487212707001282`). The check: `|e|·(δa + δc) + |e·ln b|·(δp + δq) > 2^-53`, each δ the operand's exact relative cast loss from int64. e2e probe, 3000 random powers with operands near and past `2^53` against mpmath at 60 digits, 742 double results: before the check, 315 more than 1 ulp off; thresholds `2^-51`, `2^-52`, `2^-53`, `2^-54` flag 9, 17, 53, 123 results within 1 ulp and miss 22, 5, 0, 0 wrong ones. With the check at `2^-53`, none more than 1 ulp off passes and 377 raise. `3^(9007199254740995/9007199254740994)` (1 ulp, `3.000000000000001`) is one of the correct results that now raise.
