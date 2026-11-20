# Real root

## Why the real arms take the root as a power (2026-11-19, master b00725b)

`Calculator::root(double, double)` (`transcendental.cpp:45-57`) is `pow(x, 1.0 / y)` (`std::pow`), and `Calculator::root(const BigReal &, const BigReal &)` (`transcendental.cpp:130-141`) is `pow(x, BigReal(1) / y)` (Boost `pow`, `exp(y * log(x))`), at every degree, 2 and 3 included, although `Calculator::sqrt(double)`, `Calculator::cbrt(double)` and `Calculator::sqrt(BigReal)` exist. Both bodies date from the first native layout (12ba95d, 2025-12); later commits changed only the domain checks (c92ceb4, 43abe1b, 305c1ef, e10b79a). The exact path for an integer degree (#223, #225, spec `2026-11-10-complex-root-exact-design.md`) was written for the Complex and BigComplex arms only: the issue and the spec name the complex noise, and neither says the real arms are left on `pow` on purpose. No spec, finding or issue records a choice for the real arms.

## Seen e2e (2026-11-19)

- `(1e300)⌄3` is `float 9.999999999999872e+99`, shown `9.9999999999998719e+99`; the correctly rounded root of the double `1e300` is `1e+100`, 66 ulps away.
- `123456789⌄9` is `7.926057519414247`, one ulp under the correctly rounded `7.926057519414248`.
- `(8*10^300)⌄3-2*10^100` is `BigReal 5.701408897878931e+52`, exact `0` (relative `2.85e-48`, inside the 50 digits).
- `M^(-1/3)` with M `-9223372036854775807-1` is a BigReal `2.9e-63` off `-4.76837158203125e-7`: the real-first rewrite builds `M⁻¹` in BigReal and roots it with the BigReal kernel (#249).

## Candidates (2026-11-19)

Scratch probe, `g++ -std=c++20 -O2`, std and Boost only, no TCalc code. 20 rows at degrees 2 to 20 (`8`, `27`, `2`, `3`, `10`, `0.001`, `1e300`, `1e-300` and `2^-63` at 3; `64` at 6, `1024` at 10, `3^20` at 20, `2` at 7, `100` at 5, `1.5` and `2` at 2, `7.389056098930650` at 4, `123456789` at 9, `0.5` and `9223372036854775807` at 3), against mpmath at 120 digits. Double: equal to the correctly rounded value. BigReal: worst relative error.

- Double `std::pow(x, 1.0 / n)` (today): 14 of 20, 12 ns.
- Double `sqrt` at 2, `cbrt` at 3, `pow` elsewhere: 15 of 20, 12 ns. glibc `cbrt(27)` is not `3`.
- Double `pow` guess and one Newton step in double: 15 of 20, 36 ns.
- `pow` guess and one Newton step in `long double`, `z^(n-1)` by squaring, rounded to double: 20 of 20, 20 ns. With `std::pow` for `z^(n-1)` and two steps: 20 of 20, 387 ns. On arm64 macOS `long double` is `double` (`complex-root.md`); not measured there.
- BigReal `pow(x, 1/n)` (today): worst `9.7e-48` (`1e-300` at 3), `2.9e-48` (`1e300` at 3), 30.8 µs.
- BigReal `pow` guess and two Newton steps: worst `3.6e-65`, 32.5 µs.
- BigReal `boost::math::cbrt` at 3: worst `2.6e-65`, 4.3 µs.

## More cases, e2e (2026-11-19, fix/real-root-precision on master 6c52bd7)

Measured through the editor's plain text and `evaluate_branch`, against mpmath at 80 digits. Double, ulps off the correctly rounded root: `(1e300)⌄3` 66, `(-1e300)⌄3` 66, `(1e-300)⌄3` 101, `(1e300)⌄(-3)` 100, `(1e100)⌄7` 12, `9223372036854775807⌄3` 4, `123456789⌄9` 1, `(-10)⌄5` 1. Already correctly rounded: `2⌄3`, `3⌄3`, `10⌄3`, `(0.5)⌄3`, `2⌄2`, `(1.5)⌄2`, `2⌄7`, `100⌄5`, `5⌄10`, `2⌄(-3)`, `(2.5)⌄4`, `17⌄6`, `(-2)⌄3`. BigReal, exact root minus its value, exact `0`: `(8*10^300)⌄3-2*10^100` `5.701408897878931e+52`, `(-8*10^300)⌄3+2*10^100` `-5.701408897878931e+52`, `(10^300)⌄3-10^100` `2.850704448939466e+52`, `(10^400)⌄4-10^100` `7.377101126755206e+51`, `(32*10^500)⌄5-2*10^100` `3.116140621308291e+51`, `(10^600)⌄6-10^100` `-2.708935449317851e+51`, `(10^300)⌄(-3)-10^(-100)` `-2.850704448939466e-148`, `(4*10^200)⌄2-2*10^100` `5.451437342513802e+52`. `(2*10^300)⌄3` and `(3*10^400)⌄7` match mpmath in the digits shown.

## Edges of the Newton step (2026-11-19)

- A negative degree needs no reciprocal: the step on `z^n - x` with `n = -3` from the `pow` guess gives `1e-100` for `1e300`, `0.7937005259840998` for `2`, `0.5` for `8` in `long double`, and `0` off for `1e300`, `8` in BigReal with the 50-digit check (probe `neg.cpp`).
- Degree 2 needs no `sqrt` branch in BigReal: the Newton step with the 50-digit check gives `root(4e200, 2) - 2e100` = `0`.
- A zero radicand reaches the BigReal arm: `(1e300*0)⌄3` is `BigReal 0`, since the range rule reads `log10(0)` and promotes. No double zero radicand reaches the double arm by that rule.
- Degree 0 is a Math Error before the kernel computes anything (`require_nonzero`), `(1e300)⌄1` is `1e+300`.

## Where pow's root passes 1 ulp (2026-11-19)

400000 roots, `x` log-uniform in `1e-40..1e40`, degree `-20..20` (not `-1, 0, 1`), `std::pow(x, 1.0/n)` against a 50-digit reference (probe `ilogb.cpp`). Up to `|ilogb(x)|` 8 no root is more than 1 ulp off (worst 1.00); from 9 on some are 2 or 3 ulps off (9: 2 of 2825, 12: 19 of 2731, 19: 103 of 2738). By `|ln x|` over `1e-300..1e300` (probe `thresh.cpp`): wrong by any amount 1.7% under 1, 21.4% at 5..10, 78.6% at 100..301; more than 1 ulp 0% under 5, 75.7% at 100..301.

## Boost's Newton against the hand step (2026-11-19)

`boost::math::tools::newton_raphson_iterate` in `long double`, from the `pow` guess, with `z^n` by squaring and the derivative `n * p / z`, gives the same double as the hand step on all 25 positive rows of the probe (probe `bnewton2.cpp`), 25 of 25 correctly rounded there, and `0.99999999967722819` at degree `-2147483648`. It runs slower than one hand step (125 against 101 ns, 198 against 135 ns in two runs, both with `stod`). With `std::pow` for `z^n` it is 275 ns. `powl(x, 1.0L/n)` with no Newton is 25 of 25 at 232 ns; `sqrt`, `cbrt` (glibc's `cbrt(27)` is not `3`) and `pow` is 18 of 25 (probe `nonewton.cpp`).

In BigReal, the same Boost call with the 50-digit check gives exactly `0` off on `8e300`, `-8e300`, `1e300` at 3, `1e400` at 4, `3.2e501` at 5, `1e600` at 6, `1e300` at -3, `4e200` at 2, `27` at 3, `8` at -3, `2^-63` at 3, `64` at 6, `1024` at 10, and matches mpmath to 50 digits on `2e300` at 3 and `3e400` at 7; 59.0 us against `pow`'s 53.9 us (probe `bigboost.cpp`).

## A zero radicand needs no branch (2026-11-19)

`(1e300*0)⌄3` reaches the BigReal root (the range rule reads `log10(0)`). With `newton_raphson_iterate`, its guess `pow(0, 1/3)` is `0` and `f(0)` is `0`, so Boost returns the guess before the derivative's `0 / 0`. A `x != 0` branch was written and then removed: without it `root(0, 3)` and `(1e300*0)⌄3` both stayed `0` (`make native-test`, `pytest -k root-cube-zero-radicand`).

## The Newton rounds twice (2026-11-19)

The Newton result is a `long double` rounded to double, so a root near the midpoint of two doubles can land on the midpoint and the tie goes the wrong way. Review found `(1.7976931348623157e308)⌄2` `1.3407807929942597e+154` and `(4.042789004645595e299)⌄2` `6.358293013573372e+149`, one ulp off where `pow(x, 0.5)` was right. Over 268626 random roots above the bound, degree not 2, against an 80-digit reference converted with `strtod` (probe `regr.cpp`; `static_cast<double>` of a `cpp_dec_float` is not correctly rounded and first showed `std::sqrt` wrong on 6 of 7046): pow right and Newton wrong 9, pow wrong and Newton right 210653, both wrong 56; `std::sqrt` at degree 2 wrong on 0 of 7046.

Taking the side of a midpoint `z` from the sign of `z^n - x` (probe `regr_mid.cpp`): pow right and Newton wrong 4 (degree 8 three times, 17 once), both wrong 25. Cost per root on the Newton branch: `pow` 12.7 ns, Newton 57.2 ns, Newton with the midpoint check 68.3 ns. The 4 left are the Newton's own last `long double` bit; they stay within 1 ulp. Inputs the check fixes, from `midcases.cpp`: `(4.5699183073566334e170)⌄4`, `(7.4762568165974985e-159)⌄(-4)`, `(2.114202629437795e-81)⌄16`, `(2.8842032797071242e-41)⌄(-20)`.

## What the midpoint check picks (2026-11-19, whole-branch review)

Over 300000 roots above the bound in `long double` (review probe `rev/b.cpp`), 176 landed on a midpoint of two doubles. The sign of `z^n - x` picks the right side on 157 of them, plain rounding on 88. In 32 `z^n - x` is exactly `0`, the sign says nothing and the upper side wins for a positive degree (right in 20); where it is not `0` the sign is wrong in 7 of 144. `(4.5699183073566334e170)⌄4` is one of the `0` cases. An early `r == z` return before the check changed no result in the same sweep and was removed.
