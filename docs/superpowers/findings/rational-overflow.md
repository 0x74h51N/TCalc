# Rational overflow

## 2026-11-17, fix/rational-overflow: ops with no BigReal arm reject the widened results

Found by the whole-branch review. Through the app path, master against the branch at 50e3749: `atan(3^{40})` `1.5707963267948966` against `Math Error: unsupported operand type for atan`, and the same for `asin((1/3)^{40})`, `acos((1/2)^{64})`, `sinh(1/10^{19})`, `cosh(1/10^{19})`, `tanh(2^{64})`, `asinh(9223372036854775807+1)`, `acosh(10^{19})`, `atanh(1/(3037000500*3037000500))`, `cbrt(3^{42})` and `atan(intdiv(1e16,1))`. The #245 retry makes these operands BigReal, and `coerce` rejected a BigReal for an op with no BigReal arm. `coerce` now runs such an op in double when the BigReal converts to a double that neither overflows nor loses its range: all of them give master's value again, `asin((1/3)^{40})` a closer one (`8.225263339969959e-20`, master `8.22526333996994e-20`), and the literal `atan(10000000000000000000)`, an error on master, is `1.5707963267948966`. `atan(10^{400})` and `cbrt(10^{400})` stay an error. The demoted operand goes on through `coerce` as a double, so `nCr(3^{40},2)` keeps master's `choose is only defined for integers`; returning right after the demotion gave `unsupported operand type for choose`. `BigReal::convert_to<double>()` gives 0 below `DBL_MIN`, never a subnormal (`1e-310`, `8.7e-311` and `2.2e-308` all give `0`), so the check is inf or a zero from a nonzero BigReal; `atan(10^{400}-10^{400})`, a BigReal zero, is `0.0`.

## 2026-11-17, fix/rational-overflow: intdiv's operands were the problem, not atan

Through `calc_native.apply` (no LaTeX): on master `atan(int 1)` and `atan(Rational 1)` are `0.7853981633974483`, `atan(BigReal 1)` is the error `unsupported operand type for atan`. A first #252 fix widened intdiv to BigReal by the operands' magnitude, so `intdiv(10^{18},10^{18})` became `BigReal 1` and `atan` of it failed. `intdiv(2^{62},3)` is `1537228672809129216` on master (exact `1537228672809129301`), the same as Python's `int(float(2**62)/3.0)`: the division ran in double. An exact `intdiv(Rational, Rational) -> int64` kernel (int256 division, truncated toward zero) gives `int 1537228672809129301`, `intdiv(10^{18},10^{18})` `int 1`, `intdiv(7/2,1/3)` `int 10`, `intdiv(-7,2)` `int -3`; a quotient past int64 overflows it and retries in BigReal, exact: `intdiv(int64 min,-1)` is `9.223372036854776e+18`, `intdiv(9223372036854775807,1/2)` is `1.844674407370955e+19`.

## 2026-11-17, fix/rational-overflow: approaches rejected

- A Rational return for intdiv (copied from `div`'s shape) stored every integer quotient as `x/1`; the kernel returns `std::int64_t`.
- A retry rule that read the operands' precision sent a fractional power such as `2^(0.1)` to BigReal; `atan`, `asin`, `acos`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh` and `atanh` have no BigReal arm and failed on it. The retry now reads only the exponent: a whole one is rational and retries in BigReal, any other one retries in double. The e2e rows `*-of-fractional-power` keep it.
- Skipping `promote_big` for every op whose operands are only Int64 or Rational turned `pow(0,3)` from `BigReal 0` into `Rational 0` and let `root(0, int64 min)` leak `bad rational: non-zero singular denominator`. The skip is limited to ops with `Trait::DoubleKernelRange` (only IntDiv); after that, 131 pow and root extremes were unchanged against master.
- `2^{3}^{2}` is not valid LaTeX (the editor builds `2^{3^{2}}`), so a chained power typed that way is not an evaluator case; evaluator questions are probed with `apply`.

## 2026-11-17, fix/rational-overflow: grid against master

223 expressions through the app path, master against the branch before the intdiv kernel: every fractional power was unchanged; the 44 changes were rational results past int64 (#245, now exact BigReal) and intdiv (#252).

## 2026-11-17, master 7a64ef8: intdiv past int64 wraps or loses digits (#252)

Through the app path (editor plain text, `evaluate_branch`, `format_result`): `intdiv(9223372036854775807,1)`, `intdiv(1e19,1)` and `intdiv(1e300,1)` are `int -9.223372036854775808e+18`; `intdiv(1e19,3)` is `3.333333333333333504e+18` (exact 3333333333333333333); `intdiv(9007199254740993,1)` is `9.0071992547409920e+15`; `intdiv(9223372036854775807,1099511627776)` is `8388608` (exact 8388607); `intdiv(-9223372036854775807,2)` is `-4.611686018427387904e+18` (exact -4611686018427387903). `intdiv(7,2)` `3`, `intdiv(-7,2)` `-3`, `intdiv(7,0)` a math error.

Calling the kernels directly (a probe linked against `libcalc_core.a`): the double kernel gives `intdiv(9223372036854775807.0, 1.0)` = `-9223372036854775808` and `intdiv(1e19, 3.0)` = `3333333333333333504`, and `static_cast<double>(9007199254740993LL)` is `9007199254740992`, so an Int64 operand loses its digit before the division. The BigReal kernel is exact: `intdiv(BigReal("9223372036854775807"), BigReal("1099511627776"))` = `8388607`, `intdiv(BigReal(1e19), BigReal(3))` = `3333333333333333333`, `intdiv(BigReal("-9223372036854775807"), BigReal(2))` = `-4611686018427387903`; `intdiv(BigReal(1e300), BigReal(1))` is the double's value, `1.00000000000000005250476e+300`.

## 2026-11-17, master 7a64ef8: more #245 cases through the app path

`2^{63}` and `2^{63}-1` are `float 9.2233720368547758e+18`; `(-2)^{63}` is `float -9.2233720368547758e+18`, though it fits int64; `9223372036854775807+1` is a float; `9223372036854775807*9223372036854775807` is `float 8.5070591730234616e+37`; `3^{40}*3^{40}` is `float 1.4780882941434593e+38`; `9223372036854775807/(1/2)` is `float 1.8446744073709552e+19`; `(-3)^{41}+36472996377170786403` is `BigReal -1949`. `3^{39}` and `10^{18}` stay Rational, `4^{1/2}` is `Rational 2`. `str` of a BigReal from Python shows 16 digits and the binding has no `==`, so an e2e check of a value past 16 digits goes through a difference.

## 2026-11-16, master 552eb93: an exact result past int64 is retried in double (#245)

A Rational kernel that cannot hold its result in int64 throws, and `apply`'s retry (`eval.cpp`, the `catch` after the kernel) runs the op again on `as_double` operands. A double holds an integer exactly only up to $2^{53}$, so the value is wrong from there and every op after it carries the error. Add, Sub, Mul and Div find the overflow through `WideRational` and `narrow` (`calc/internal/helpers.hpp`), Pow through `rational_pow_overflows`; all of them throw the same `math_error()` an irrational root throws, so the retry cannot tell them apart. `power_needs_big` widens a power to BigReal before the kernel only past $10^{308}$, or for base 10 with an exponent of 308 or more.

Through the app path (editor plain text, `evaluate_branch`, `format_result`):

- `3^{40}-12157665459056928801` is `BigReal -33` (exact 0); `3^{40}` is `float 1.2157665459056929e+19`.
- `9223372036854775807+2-9223372036854775809` is `BigReal -1` (exact 0).
- `3037000500*3037000500-9223372037000250000` is `BigReal -656` (exact 0).
- `(1/3)^{40}*3^{40}` is `float 0.999999999999998` (exact 1).
- `10^{19}` is `float 1e+19`, while the literal `10000000000000000000` is `BigReal 1e+19`.

`apply(Pow, Rational(10), Rational(18))` is `Rational`, `Rational(19)` is `float 1e+19`: the boundary is int64, not $2^{53}$.

The BigReal arm keeps these exact up to its 50 digits: `apply(Sub, apply(Pow, BigReal(3), BigReal(40)), BigReal(12157665459056928801))` is `BigReal 0`. Past 50 digits it rounds (`7^{60}` has 51).

## 2026-11-16, prototype on 552eb93: the retry widened into BigReal

A throwaway worktree changed only the retry: Add, Sub, Mul, Div, and Pow with a whole exponent, rerun through `redispatch_big` with `lift_to_big` instead of `as_double`. Through the app path:

- Right now: `3^{40}-12157665459056928801`, `9223372036854775807+2-9223372036854775809`, `3037000500*3037000500-9223372037000250000`, `(-3)^{41}+36472996377170786403` are `BigReal 0`; `(1/3)^{40}*3^{40}`, `(2/3)^{50}*(3/2)^{50}`, `(3/2)^{100}*(2/3)^{100}` are `BigReal 1`; `0.0000000001 * 0.0000000001` is `BigReal 1e-20` (was `1.0000000000000001e-20`); `3^{40}*i` is `BigComplex 0+1.215766545905693e+19i`.
- Unchanged: `2^{1/2}` and `sqrt(2)` double, `4^{1/2}` `Rational 2`, `10^{18}` and `2^{40}` Rational, `0^{-1}` and `1/0` a math error.
- `gcd(3^{40},3)` becomes the math error `gcd is only defined for integers`; on master it aborts the process (below).
- Red: native `pow(2, 64) overflows the exact arm into a double` and `mul of two small rationals overflows the kernel, recovers as double`; e2e `pow-large-exp-stays-float` (`2^309`), `float-div-keeps-float` (`(10^307)/(10^306)`), `log-of-its-own-power-implicit-base` (`log(10^{21})`), and five rows of `TestRational::test_downcasts_to_float`. Each one is a type change from float to BigReal, with the same or a closer value.
- A power of two past 50 digits now shows the BigReal guard-digit noise in a cancellation: `2^{309}-2^{308}*2` is `BigReal -3.8726059e+23` (master `float 0`, the double holds a power of two exactly); `apply` on BigReal operands gives `2^{k}-2^{k-1}*2` = 0 for $k$ = 200 and 257, `21325312` for 250, `1.9e+23` for 300. The same noise is on master past double's range: `2^{1100}-2^{1099}*2` is `BigReal 4.659688e+262`, `3^{700}-3^{699}*3` is `BigReal 2.44251874e+264`.

## 2026-11-16, master 552eb93: gcd of a double past int64 aborts

`gcd(1e19,3)`, `gcd(3^{40},3)`, `gcd(2^{63},2)` and `lcm(10^{19},3)` end the process: `numeric:130: std::__detail::__abs_r ... Assertion '__val != __gnu_cxx::__int_traits<_Res>::__min' failed`. The double reaches `std::gcd` as INT64_MIN. `gcd(10000000000000000000,3)` (a BigReal) is the math error `gcd is only defined for integers`, and `gcd(9223372036854775807,3)` is `1`.

Not a regression: `number_theory.cpp` is the same in v0.13.2 and master. The build type decides what is seen. A Debug build of f1777e0 aborts on `gcd(1e19,3)`; a Release build of the same commit (`~/.local/opt/tcalc`, `CMAKE_BUILD_TYPE=Release`) gives `gcd(1e19,3)` `1`, `gcd(2^{63},2)` `2`, and `lcm(10^{19},3)` `-9.223372036854775808e+18` (exact `3e+19`). `std::llround` of a double past int64 gives INT64_MIN on x86-64; libstdc++ 15 asserts on its absolute value in an unoptimized build, and a Release build goes on with undefined behavior.

## 2026-11-16, master 552eb93: factorial past 20 is a double

Fixed on fix/factorial-exact (#261): a whole number is exact, an integer up to 20! and a BigReal past it. The measurements are in [combinatorics.md](combinatorics.md).
