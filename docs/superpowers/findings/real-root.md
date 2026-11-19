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
