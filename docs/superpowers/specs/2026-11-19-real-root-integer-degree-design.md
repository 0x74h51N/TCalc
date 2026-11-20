# The real root at an integer degree

Milestone: First release. Issue: #271. Measurements: [real-root.md](../findings/real-root.md).

## The bug

`Calculator::root(double, double)` (`transcendental.cpp:45-57`) and `Calculator::root(const BigReal &, const BigReal &)` (`transcendental.cpp:130-141`) compute every root as `pow(x, 1/y)`. `1/y` is rounded (`1/3` has no finite binary or decimal form), and `pow` is `exp(y * log(x))`, so a root at an integer degree loses digits, an exact root included. The Complex and BigComplex arms already take an integer degree exactly (#223, #225: `sqrt`, `integer_power`, `newton_root`); the real arms were left out of that work, and nothing records it as a choice (findings `real-root.md`).

Every case below was measured e2e (editor plain text, `tokenize`, `evaluate_branch`) against mpmath at 80 digits; each one becomes a test row, the correct ones included.

Double arm, against the correctly rounded root:

| Input | Expected | Today |
|---|---|---|
| (1e300)⌄3 | 1e+100 | 9.999999999999872e+99 |
| (-1e300)⌄3 | -1e+100 | -9.999999999999872e+99 |
| (1e-300)⌄3 | 1e-100 | 1.0000000000000128e-100 |
| (1e300)⌄(-3) | 1e-100 | 1.0000000000000127e-100 |
| (1e100)⌄7 | 193069772888325.03 | 193069772888324.66 |
| 9223372036854775807⌄3 | 2097152.0 | 2097151.9999999984 |
| 123456789⌄9 | 7.926057519414248 | 7.926057519414247 |
| (-10)⌄5 | -1.5848931924611134 | -1.5848931924611136 |
| 2⌄3 | 1.2599210498948732 | same |
| 3⌄3 | 1.4422495703074083 | same |
| 10⌄3 | 2.154434690031884 | same |
| (0.5)⌄3 | 0.7937005259840998 | same |
| 2⌄2 | 1.4142135623730951 | same |
| (1.5)⌄2 | 1.224744871391589 | same |
| 2⌄7 | 1.1040895136738123 | same |
| 100⌄5 | 2.51188643150958 | same |
| 5⌄10 | 1.174618943088019 | same |
| 2⌄(-3) | 0.7937005259840998 | same |
| (2.5)⌄4 | 1.2574334296829355 | same |
| 17⌄6 | 1.6035216215125492 | same |
| (-2)⌄3 | -1.2599210498948732 | same |

BigReal arm:

| Input | Expected | Today |
|---|---|---|
| (8\*10^300)⌄3-2\*10^100 | 0 | 5.701408897878931e+52 |
| (-8\*10^300)⌄3+2\*10^100 | 0 | -5.701408897878931e+52 |
| (10^300)⌄3-10^100 | 0 | 2.850704448939466e+52 |
| (10^400)⌄4-10^100 | 0 | 7.377101126755206e+51 |
| (32\*10^500)⌄5-2\*10^100 | 0 | 3.116140621308291e+51 |
| (10^600)⌄6-10^100 | 0 | -2.708935449317851e+51 |
| (10^300)⌄(-3)-10^(-100) | 0 | -2.850704448939466e-148 |
| (4\*10^200)⌄2-2\*10^100 | 0 | 5.451437342513802e+52 |
| (2\*10^300)⌄3 | 1.259921049894873e+100 | same |
| (3\*10^400)⌄7 | 1.625613593056498e+57 | same |
| (1e300\*0)⌄3 | 0 | same |

`M^(-1/3)+1/2097152`, with M `-9223372036854775807-1`, is `-2.89795463e-63` on #249's branch, exact `0`; it needs that branch and is not a row here.

## How a root reaches these arms

`apply` (`eval.cpp`) lifts integer operands to `Rational`, and `Calculator::root(Rational)` (`arithmetic.cpp:203`) tries the exact root first (`try_rational_pow`). When it refuses, `Root` has no retry arm, so the retry runs in double (`ops.hpp:963`). A BigReal operand, or the range rule `power_needs_big(x, 1/y)` (`ops.hpp:1049`) through `promote_big`, sends the root to the BigReal arm. The range rule reads `log10(0)` too, so a zero radicand from double (`(1e300*0)⌄3`) arrives in BigReal. A negative radicand at an even degree leaves for the complex arms through the domain rule and is not part of this spec.

## The fix

Both kernels keep their order of checks: degree 0 and a zero radicand at a negative degree are refused, a negative radicand at a reciprocal degree (`whole(1 / y)`) stays the integer power it is, and a negative radicand at an odd degree is minus the root of `-x`. The change is the root of a positive radicand, today `pow(x, 1 / y)`, on both the positive path and the odd-degree path. The correction is Boost's `boost::math::tools::newton_raphson_iterate` on `z^n - x` from the `pow` guess; TCalc writes no Newton step of its own.

1. Double: 1 ulp is accepted. `pow(x, 1.0 / y)` stays the root, and Newton runs only where `pow` passes 1 ulp: when the degree is an integer n (`calc_detail::as_int(y)`) and `|ilogb(x)|` is at least 9, a named constant. Up to 8 no measured root is more than 1 ulp off; from 9 on they reach 2 and 3 ulps, and at `|ln x|` past 100 three quarters of them are more than 1 ulp off (findings `real-root.md`). `ilogb` reads the exponent and costs next to nothing, so a root of a radicand near 1 pays nothing. Degree 2 is `this->sqrt(x)` at any magnitude: `std::sqrt` is correctly rounded, and the Newton is not there (`(1.7976931348623157e308)⌄2`). The Newton runs in `long double`, `z^n` by repeated squaring (`std::pow(long double, int)` is `exp(log)` again: 275 ns against 125), and the derivative is `n * p / z` from that same `p`, so no `n - 1` overflows at degree `-2147483648`. The result is rounded to double; a `long double` result on the midpoint of two doubles would round twice, so there the sign of `z^n - x` picks the side (`(7.4762568165974985e-159)⌄(-4)`); it picks the right one on 157 of 176 midpoints, against 88 for plain rounding, and where `z^n - x` is exactly `0` it has nothing to read and takes the upper side for a positive degree. Measured over 268626 roots above the bound: 4 stay 1 ulp off where `pow` was right, 210684 are fixed; the Newton branch costs 68.3 ns against `pow`'s 12.7 ns (findings `real-root.md`).
2. BigReal: when the degree is an integer n (`calc_detail::as_int` on `calc_detail::snap_integer(y)`, since a quotient degree such as `9e400/3e400` sits under 3 in the guard digits, as the test `bigreal :: root of a negative takes a quotient degree` shows), the root is the Newton from the `pow(x, BigReal(1) / n)` guess, with Boost's integer `pow`. It has no magnitude bound: a BigReal radicand is mostly past double's range, where `pow` is off, and an exact root comes out exact only through the check that follows. The result is rounded to its 50 advertised digits (`BigReal(z.str(kBigRealPrecisionDigits))`); when that rounded value raised to n equals x, it is returned, otherwise the Newton value is. Any other degree stays `pow(x, BigReal(1) / y)`. A zero radicand needs no branch: `(1e300*0)⌄3` arrives here, its guess is `0`, and `newton_raphson_iterate` returns the guess when `f` is `0`, before the derivative's `0 / 0` (removing a zero branch turned no test red).
3. A `newton_root(double, int)` and a `newton_root(const BigReal &, int)` sit beside the BigComplex `newton_root` in `transcendental.cpp`'s anonymous namespace; each is the one call to Boost with its function and bounds. No header, helper, error kind or op table row changes, and nothing is renamed.

No branch for degree 2 or for a negative degree: the Newton from the `pow` guess gives `root(4e200, 2) - 2e100` = `0` in BigReal, and a negative n is handled by the iteration itself (`1e300` at `-3` is exactly `1e-100`).

Measured (findings `real-root.md`): Boost's Newton gives the same double as a hand step on all 25 probe rows; in BigReal, 59.0 us against `pow`'s 53.9 us, and every exact root in the rows comes back exact.

## What the user sees

The type of a result does not change: a double root stays double, a BigReal root stays BigReal. The digits do: every row of the tables above shows its Expected column, apart from `(-10)⌄5`, whose radicand is under the bound and whose `pow` root is the accepted 1 ulp off.

## Not in this spec

- #231: an exact exponent `p/q` that drops to one double when the exact arm refuses, the parity of `q` past `2^53`, and #263. That work uses this root.
- A root near 1 that collapses to `1.0` in double (#249's branch): the range rule's side, not the kernel's.
- The `cbrt` op and its BigReal arm (#229).
- On arm64 macOS `long double` is `double` (findings `complex-root.md`), so the double Newton there runs in double (15 of 20 in the findings). Not measured on macOS.

## Tests

Written first and run before the fix: every row with a wrong Today value is red but `(-10)⌄5` (the accepted 1 ulp), every row marked "same" is green and stays green after the fix.

- End to end, `tests/py/e2e/test_eval_e2e.py`:
  - The BigReal table goes into `test_bigreal_exact_results` as rows of `(expr, expected text)`, which compares the exact BigReal through `Decimal`: the eight `0` rows, `(2*10^300)⌄3` `1.259921049894873e+100`, `(3*10^400)⌄7` `1.625613593056498e+57`, and `(1e300*0)⌄3` `0` (green before and after: it pins the zero radicand on the Newton path).
  - The double table goes into a new parametrized test, `test_root_correctly_rounded`, whose rows are a frozen dataclass `RootCase(expr, expected, ulps)`: it asserts the type is `float` and `abs(out - expected) <= ulps * math.ulp(expected)`. `ulps` is 0 for every row but `(-10)⌄5`, which is 1. It is a new function because the golden table compares a float with `pytest.approx`, which accepts the rows several ulps off, and changing that comparison reaches every golden row; `test_log_inverse_exactness_the_golden_table_cannot_pin` is the same case already in the file.
- Native, layer by layer, `src/native/tests/unit/test_transcendental.cpp`:
  - `real_bin_cases`, `tol` 0, one row per double table row and per row of the review's cases (`(1.7976931348623157e308)⌄2` `1.3407807929942596e+154`, `(4.042789004645595e299)⌄2` `6.358293013573371e+149`, and the midpoint cases `(4.5699183073566334e170)⌄4` `4.623566508069751e+42`, `(7.4762568165974985e-159)⌄(-4)` `3.4007832048414286e+39`, `(2.114202629437795e-81)⌄16` `9.074478228903526e-06`, `(2.8842032797071242e-41)⌄(-20)` `106.41398492378998`), all also in the e2e table, with the operands as the double kernel receives them (`root(1e300, 3)`, `root(0.5, 3)`, ...); `root(-10, 5)` has `tol` `std::numeric_limits<double>::epsilon()`, one ulp at its magnitude. A row `root(2, -2147483648)` `0.9999999996772282` covers the degree whose `n - 1` would overflow.
  - A new `BigBinCase` table (`id`, `fn`, `x`, `y`, `expected` as text, a null `tol` for exact equality, otherwise the absolute tol of `approx_big`), the shape of `BigCase` with a second operand: `big_cases` holds only unary calls, and `root` is the binary BigReal call with rows. It takes the single case `bigreal :: root negative odd degree` (`root(-27, 3)` `-3`), now exact, and the rows `root(8e300, 3)` `2e100`, `root(-8e300, 3)` `-2e100`, `root(1e300, 3)` `1e100`, `root(1e400, 4)` `1e100`, `root(3.2e501, 5)` `2e100`, `root(1e600, 6)` `1e100`, `root(1e300, -3)` `1e-100`, `root(4e200, 2)` `2e100`, `root(0, 3)` `0`, and the irrational `root(2e300, 3)` `1.25992104989487316476721060727822835057025146470150798008197511216e100` at tol `1e40` and `root(3e400, 7)` `1625613593056498357175533955454820663630388491453130156256.14649566` at tol `1e-3` (66 digits from mpmath). The tolerance sits under the 50th digit, so these two rows go red when the kernel returns the 50-digit rounded value of an irrational root instead of the Newton value.
  - `bigreal :: root of a positive takes a quotient degree` (`root(8e300, 9e400/3e400)` `2e100`) and its e2e row `(8*10^300)⌄(9*10^400/(3*10^400))-2*10^100` `0` cover `snap_integer` on the positive path.
  - `bigreal :: root of a negative takes a quotient degree` stays a single case, since its degree is the computed quotient `9e400/3e400` and a text operand cannot carry that residue; it now asserts `EXPECT_EQ` with `-2`.
- Once this merges, #249's branch takes master, and its commented row `pow(int64 min, -1/3) is exact in BigReal` comes back there.
