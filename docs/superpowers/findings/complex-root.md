# Complex root

## Where the noise comes from (2026-11-11, master 9f7c4b3)

`Calculator::root(Complex)` (`transcendental.cpp`) is `this->pow(x, 1.0 / y)`, `Calculator::pow(Complex)` (`arithmetic.cpp`) is `std::pow`, and libstdc++ sends that to glibc `cpow`, which is `exp(y * log(x))`. The angle of `log(x)` carries a rounded π, so cos and sin of the divided angle are off: `(-4) ⌄ 2` is `1.2246467991473532e-16 + 2i`. The modulus is off too: `125^(1/3)` is `4.999999999999999`.

`√` (`OpId::Sqrt`, `Calculator::sqrt`, `std::sqrt`) is exact; `\root{x}{}` (`LatexKind::Root`) gets degree 2 at `eval.cpp:462` and goes to `OpId::Root`, so it takes the `pow` path. `format_result` hides a part below `1e-12`, so `\root{-4}{}` shows `2i` while `\root{-1e20}{}` shows `6.1232339957367680e-07+1.0000000000000004e+10i`.

Neither std nor Boost has a complex n-th root: std has complex `sqrt` only, `boost/math/complex/` has the inverse trig and hyperbolic functions and `fabs`, and the Boost.Multiprecision complex `pow` is `exp(log)` too (`(-4) ⌄ 2` in BigComplex: real part `4.3e-51`).

## Candidates on the degree 3 and up rows (2026-11-11)

Scratch probes, `g++ -std=c++20 -O2`, linked to `src/native/build/native/libcalc_core.a` where Calculator is used. 16 rows of `complex_root_cases` at degree 3 and up, compared exactly with the principal root computed at 400 bits by mpmath and rounded to double.

- `std::pow` (today): 4 of 16. 20 to 46 ns.
- `pow` guess, then `boost::math::tools::complex_newton` on `z^n - x` in double (`std::pow(z, int)` is libstdc++ binary exponentiation, multiplications only): 13 of 16, 80 to 130 ns, 2 or 3 calls of the function. Fails where a part is irrational: `(-8) ⌄ 3` gives `0.99999999999999989+1.7320508075688774i`, `(-1) ⌄ 4` gives `0.70710678118654757+0.70710678118654746i`, `(-16) ⌄ 4` gives `1.4142135623730951+1.4142135623730949i`. At the correctly rounded root `z^n - x` is not 0 in double, so Newton stops on another point.
- Failed: axis radicands through half turns (`r = pow(|x|, 1/n)` refined by one real Newton step, cos and sin by `Calculator::real_half_turns`), Newton elsewhere: 9 of 16, 146 ns. `real_half_turns` is not correctly rounded: `cos(π/4)` is `0.70710678118654757`. Only `exact_half_turns` is exact, and only for rational values.
- The same Newton in `std::complex<long double>`, rounded to double: 16 of 16, 268 ns.
- The same Newton in `cpp_complex_50`, rounded to double: 16 of 16, 14 µs.

On x86-64 Linux `long double` is the 80-bit format; on arm64 macOS it is the same as `double`, where the long double result would fall back to 13 of 16. Not measured on macOS.

## Degree 2 (2026-11-11)

`std::sqrt` on Complex: 3 ns (15 ns on `-117+44i`), exact on every degree 2 row. `cpp_complex_50` `sqrt`: 0.5 to 1 µs, against 2 to 52 µs for its `pow`.

## Negative and fractional degrees, degree 1e30 (2026-11-11)

Same probes.

- A negative integer degree goes through the same `cpp_complex_50` Newton with a negative `n` (`pow(z, int)` takes it): `(-4)` at `-2` is `-0.5i`, `(-1)` at `-4` is `0.7071067811865476-0.7071067811865476i`, `(-117+44i)` at `-3` is `0.12-0.16i`, all exact.
- A degree whose reciprocal is an integer is a power, not a root: `std::pow(x, int)` gives `(-4)` at `0.5` as `16`, `(-117+44i)` at `0.5` as `11753-10296i`, `(-4)` at `0.25` as `256`, `(-4)` at `-0.5` as `0.0625`, all exact. `cpow` gives `15.999999999999998-3.9188697572715295e-15i` for the first.
- `(-1)` at `1e30`: the kernel gives `1+3.1415926535897927e-30i`, one ulp below the correctly rounded `3.141592653589793e-30`, because `1/1e30` is `9.9999999999999991e-31` in double. Both show as `3.141592653589793e-30`. The human agent ruled it correct.

## Newton edges (2026-11-11)

- x = 0: `complex_newton` sees a zero derivative, falls to Muller's method and returns NaN. `\root{0i}{3}` reaches the Complex arm (it shows `0` today through `cpow`).
- Newton's stop test is `max(|z| eps, eps)`, absolute below 1, so a root below 1 is returned unrefined: `cpp_complex_50` Newton at degree `-2` gave `(-1e300)` a real part of `-9.5566194534729613e-299` and `(-1e-300)` one of `5.1317082433770156e-49`, where both are 0. Taking `1 / root(x, 2)` gives exact zeros.
- A double reciprocal of a correctly rounded root moves the last digit: `1 / (0.7071067811865476 + 0.7071067811865476i)` is `0.70710678118654746 - 0.70710678118654746i`, and `1 / (0.5 + 0.8660254037844386i)` is `0.50000000000000011 - 0.86602540378443871i`. In `cpp_complex_50` before the rounding to double it does not.
- `boost::multiprecision::pow(cpp_complex_50, int)` is exact at 60 digits: `(-4)^2 = 16`, `(-117+44i)^2 = 11753-10296i`, `(-4)^-2 = 0.0625`, `(3+4i)^5 = -237-3116i`.

## Integer powers past the range and negative powers (2026-11-11)

- `pow(x, int)` overflows into NaN, not inf: `std::pow(1+i, 3000)` is `inf+nan i` (`cpow` gives `inf-inf i`), and Boost `pow(-4e400, INT_MIN + 1)` is `nan+nan i` where `exp(log)` gives `0`. The integer power falls back to `pow` when its result is not finite.
- A negative integer power in double is one division off: `(-7+24i)^-2` is `-0.0013491199999999999+0.00086016i` and `(-117+44i)^-2` is `4.8140287999999991e-05+4.2172415999999993e-05i`; the same power in `cpp_complex_50`, rounded to double, is `-0.00134912+0.00086016i` and `4.8140288e-05+4.2172416e-05i`, the exact values.
- A BigReal degree that is near an integer but not one could not be typed: `1+10^{-20}` evaluates to the double `1.0`, and `1+10^{-400}` is `1` at 50 digits. So the double read of a BigComplex degree loses nothing reachable.
