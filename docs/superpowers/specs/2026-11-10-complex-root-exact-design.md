# Exact complex roots

Issues #223 and #225, milestone First release. Measurements: [complex-root.md](../findings/complex-root.md).

## The bug

`Calculator::root` on the Complex and BigComplex arms is `pow(x, 1 / y)`, and `pow` is `exp(y * log(x))` (glibc `cpow`, and the Boost.Multiprecision complex `pow`). The angle of `log(x)` carries a rounded π and the modulus a rounded power, so a root that is exact in math comes back with noise in both parts:

- `\root{-1e20}{}` shows `6.1232339957367680e-07+1.0000000000000004e+10i`; `√(-1e20)` shows `1e10 i`, because `√` is `OpId::Sqrt` and `std::sqrt`, while `\root{x}{}` gets degree 2 at `eval.cpp:462` and goes to `OpId::Root`.
- `\root{-117+44i}{3}` shows `3+4.000000000000001i`; `\root{-1+0i}{3}` shows `0.5000000000000001+0.8660254037844386i`; `\root{-1}{4}` shows `0.7071067811865476+0.7071067811865475i`.
- `\root{-4}{}` shows `2i` only because `format_result` drops a part below `1e-12`; `\root{-4}{}*10^{17}` shows `12.24646799147353+2.0000000000000000e+17i`.
- On BigComplex the formatter drops nothing: `\root{-4*10^{400}+0i}{}/10^{200}` shows `4.334833682648708e-51+2i`.

Neither std nor Boost has a complex n-th root; std has complex `sqrt` only.

## How a root reaches these arms

`apply` (`eval.cpp`) coerces integer operands to Rational, and `Calculator::root(Rational)` tries the exact root first through `try_rational_pow`. A negative radicand at an even degree has no rational root, so the Rational arm raises; the retry downcasts to double, `promote_complex` lifts the radicand to Complex, and `Calculator::root(Complex)` runs. A Complex operand (`(-117+44i) ⌄ 3`) is lifted to Complex by `coerce` directly. `promote_complex` skips a BigReal operand, so the BigComplex arm is reached only when a Complex operand is past the double range: `(-4*10^{400}+0i) ⌄ 2`.

## The fix

`root` on both complex arms takes the first step that fits the degree y, and the result stays on its arm:

1. `y == 2`: `sqrt`. It is algebraic, exact at any magnitude, and the cheapest step (3 ns against 20 to 46 ns for `pow`).
2. `1 / y` is an integer m (degree 1, -1, 0.5, 0.25, -0.5): `pow(x, m)` with an integer m, which is binary exponentiation, multiplications only. `(-4) ⌄ 0.5` is `16`. On the Complex arm a negative m goes to the BigComplex arm like step 3, because the double reciprocal `1 / x^|m|` moves the last digit (`(-7+24i) ⌄ -0.5` gave `-0.0013491199999999999`, exact `-0.00134912`). A power that is not finite falls to step 4: past the range the complex product's `inf * inf` is NaN, where `pow` keeps the inf or the underflow to 0 (`\root{-4*10^{400}+0i}{-1/2^{31}}` is `0`).
3. y is any other integer that fits an `int`, and x is not 0: the BigComplex arm, which runs Newton on `z^n - x` with `boost::math::tools::complex_newton`, starting from the `pow` guess, with `z^(n-1)` from the library `pow(z, int)`. The Complex arm calls `this->root(BigComplex(x), BigComplex(y))` and converts the result back, so its result stays Complex and the ops after it stay on the double arm. Newton in double leaves an irrational part one ulp off (`(-8) ⌄ 3`, `(-1) ⌄ 4`, `(-16) ⌄ 4`); in `cpp_complex_50` every measured row lands on the correctly rounded value. `long double` would be enough on x86-64 Linux, but on arm64 macOS it is `double`.
   - A negative degree is `1 / root(x, -y)` on the BigComplex arm, so `-2` goes through `sqrt`. Newton stops on an absolute tolerance when the root is below 1, which left `(-1e300) ⌄ -2` with a real part of `-9.6e-299`; and the reciprocal is taken in `cpp_complex_50`, because a double `1 / w` moves the last digit (`(-1) ⌄ -4` gave `0.70710678118654746`).
   - x = 0 has a zero derivative, and Newton returns NaN there; `\root{0i}{3}` reaches the Complex arm and shows `0` today, so x = 0 takes step 4, whose `pow` gives 0.
4. Everything else (a complex degree, a non-integer degree with no integer reciprocal, a degree past `int` such as `1e30`, a zero radicand): `pow`, as today.

Newton is a function in an unnamed namespace of `transcendental.cpp`, `newton_root(const BigComplex &x, int n)`. Only the BigComplex `root` calls it, so `boost/math/tools/roots.hpp` stays out of `calc/internal/helpers.hpp` and every file that includes it. The cost is about 14 µs, paid only when a root at a degree other than 2 reaches a complex arm.

`(-1) ⌄ 10^{30}` stays on `pow`: `1+3.1415926535897927e-30i`, one ulp from the correctly rounded value because `1/1e30` is not exact in double. The human agent ruled it correct.

## Tests

`complex_root_cases` and `big_complex_root_cases` in `src/native/tests/unit/test_transcendental.cpp`, asserted with no tolerance. Each expected value is the exact principal root rounded to the arm's type, computed at 400 bits; the rows are not edited to match an implementation. The Complex table covers degree 2 on the real and imaginary axes (`-4`, `-1`, `-2`, `-1e20`, `-1e300`, `-1e-300`, `2i`, `-2i`), Gaussian squares, cubes, fourth and fifth powers (also past `2^53`), axis radicands at degrees 3 to 6 and 1000, a positive real and a root with no exact form, the degree `1e30`, negative degrees (`-2` on `-4`, `-1e300` and `-1e-300`; `-3` on `-1`, `-8` and `-117+44i`; `-4` on `-1`), a fractional degree and a zero radicand. The BigComplex table covers degree 2 (`-4`, `-1`, `-4e400`, `-7+24i`), Gaussian roots at degrees 3 to 5, a positive real, a negative degree, a fractional degree and a zero radicand.

The `1e30` row expects `3.1415926535897927e-30`, the human agent's ruling above.

No e2e row: the e2e table compares a complex result with `pytest.approx`, which cannot tell an exact root from a noisy one.
