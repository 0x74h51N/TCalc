# INT64_MIN reciprocal

## 2026-11-18, fix/int64-min-reciprocal (b00725b): where the reciprocal throws

M is `-9223372036854775807-1`. Measured e2e (editor canonical form, `tokenize`, `evaluate_branch`, `format_result`): every case below raises `ValueError: bad rational: non-zero singular denominator`, and the app's controller shows it as `Invalid inputs` (seen for `(M)⁻¹` through a real `MainWindow`). The same rows through `calc_native.apply` on their op raise the same error, so the source is the op, not the LaTeX form: `\root{a}{b}` and `⌄` both tokenize to `OpId.Root`, `^{}` to `OpId.Pow`, `⁻¹` to `OpId.Recip`.

The stack at the throw (`gdb -batch -ex "catch throw" -ex run -ex bt --args python <probe> "<case>"`) shows three sites, each a `Rational(denominator, numerator)` with `-9223372036854775807-1` as the new denominator:

- `Calculator::pow`, `arithmetic.cpp:197`, a negative exponent, `Recip` included (`(M/3)⁻¹`): `M^(-1/3)` reaches it from `eval.cpp:427`, `(M/3)⌄(-8)` through `Calculator::root` and `try_rational_pow` (`helpers.hpp:381`).
- `Calculator::root`, `arithmetic.cpp:205`, the inverted degree: `(8)⌄(M/3)`.
- `tcalc::eval::apply` with `OpId::Root`, a negative radicand under a fractional degree (`eval.cpp:423`): `(-8)⌄(M/3)`.

## 2026-11-18, b00725b: a root near 1 loses its small part in double

`Root` has no retry arm, so a refused exact root retries in double (`ops.hpp:963`). `(0.5)⌄(-9223372036854775807)-1` is `float 0.0`, exact about `7.5e-20`; `(9223372036854775807)⌄(-9223372036854775807)-1` is `float 0.0`. A degree that is already a BigReal keeps it: `(2)⌄(10^30)-1` is `BigReal 6.931471805599453e-31`. Recorded on #231 (comment of 2026-11-18), the same source as #263.

## 2026-11-18, fix/int64-min-reciprocal: what each case returns after the kernel fix

`pow` and `root` take the reciprocal through `div`, so the math error reaches the retry. Measured e2e (editor canonical form, `tokenize`, `evaluate_branch`): `M^(-1)` is `BigReal -1.084202172485504e-19` (Pow with a whole exponent retries in BigReal); `M⁻¹` is `float -1.0842021724855044e-19` and `(M/3)⁻¹` `float -3.2526065174565133e-19` (Recip has no retry arm); `(1)⌄M`, `(0.5)⌄M`, `(1/3)⌄M`, `(9223372036854775807)⌄M` and `(8)⌄(M/3)` are `float 1.0`; `M⌄(-1)` is `float -1.0842021724855044e-19`; `(-1)⌄M` and `M⌄M` are `complex 1-3.4061215800865545e-19j`; `M^(-1/3)` is `BigReal -4.76837158203125e-07`; `(M/3)⌄(-8)` is `complex 0.00451485998920783-0.0018701162397455288j`. The roots near 1 keep only a double's digits (#231).

The native smoke run (`smoke_stress.cpp`) segfaulted once no case failed: `expect_msg` built its message on a pass too, and the smoke builder read `f->second` with `f == failures.end()`. While the #249 pins failed, the map was not empty and the read went unnoticed. `expect_msg` now builds the message only on a failure.

## 2026-11-18, fix/int64-min-reciprocal: the real-first rewrite

`apply` now rewrites a negative radicand's fractional degree into a power only when the degree's reciprocal fits int64 (`calc_detail::narrow`); otherwise the op takes the ordinary path. `(-8)⌄(M/3)` is `complex 1-1.0218364740259663e-18j`, and the app's text for it is `1`. `(-8)⌄(1/3)` stays `Rational -512`.

## 2026-11-18, fix/int64-min-reciprocal: each arm against the exact value

`calc_native.apply` on the op, against mpmath at 60 digits (probe: `.superpowers/sdd/2026-11-18-int64-min-reciprocal/arms.py`). The double arm gives the correctly rounded double: `M⁻¹`, `(M/3)⁻¹` and `M⌄(-1)` have relative error `0`, and the roots near 1 give `1.0`, which is the nearest double (relative error `7.5e-20` to `4.7e-18`, below half an ulp). The complex arm's imaginary parts are right to a double (`(-1)⌄M` `1.3e-35`, `(M/3)⌄(-8)` `3.6e-17`). The Big arms keep the digits: `apply(Root, [BigReal 0.5, BigReal M])` minus 1 is `7.515116790152949e-20`, `[BigReal 9223372036854775807, BigReal M]` `-4.734523577796358e-18`, and `[BigReal M, BigReal M]` is BigComplex with real part minus 1 `-4.734523577796358e-18`. No arm computes a wrong value; the digits are lost where the retry picks double for `Root` (no retry arm, `ops.hpp:963`), which is #231. The golden table's `pytest.approx` has an absolute floor of `1e-12`, so its rows with values near `1e-19` check type and not value.

## 2026-11-18, fix/int64-min-reciprocal: full precision against the correctly rounded value

Every double and complex result of the cases equals the correctly rounded double of the exact value (mpmath, 80 digits, probe `.superpowers/sdd/2026-11-18-int64-min-reciprocal/cr.py`), 0 ulps apart, so the native rows compare with `tol` 0. `pow(M,-1)` minus `BigReal("-1.08420217248550443400745280086994171142578125e-19")` is `0`; `pow(M,-1/3)` minus `BigReal("-4.76837158203125e-7")` is `-2.89795463e-63`. With the two kernel fixes put back to master's text, `make native-test` stops at `unit eval unhandled exception: bad rational: non-zero singular denominator`.

## 2026-11-18, fix/int64-min-reciprocal: a root that fits a Rational comes out inexact

Found by the final review, run e2e (`editor_canonical`, `tokenize`, `evaluate_branch`, `format_result`). With M = `-9223372036854775807-1`: `M⌄(-3)` is exactly `-1/2097152`, which fits a Rational. On master it raises `ValueError: bad rational: non-zero singular denominator`; on the branch it is `float -4.768371582031254e-07`, shown `-4.7683715820312542e-07`, 4 ulps off the exact value. `M^(-1/3)` is BigReal `-4.76837158203125e-07` (`2.9e-63` off), `M⌄(-63)` is `float -0.5` (exact). Cause: `try_rational_pow` (`helpers.hpp:381`) raises the base to p before it takes the q-th root, so `M⁻¹` is built first and does not fit int64, although the root of M does.

## 2026-11-19, fix/int64-min-reciprocal: a BigReal root is not exact

`Calculator::root(const BigReal &, const BigReal &)` (`transcendental.cpp:130-141`) is `pow(x, 1/y)`, and `1/3` is rounded in `cpp_dec_float_50` (`1/3*3-1` is `-1e-72`). Measured on `calc_native.apply`: `root(BigReal 8, BigReal 3) - 2` is `-1.740330114908986e-51`; `root(BigReal -2^-63 exact, 3)` minus `-4.76837158203125e-7` is `-2.89795463e-63`. Visible e2e: `(8*10^300)⌄3-2*10^100` is `BigReal 5.701408897878931e+52` where the exact answer is `0` (relative `2.85e-48`, inside the 50 digits). No issue covers it (titles and `gh search issues "BigReal root"`: only #226, the domain); the native tests `bigreal :: root negative odd degree` and `bigreal :: root of a negative takes a quotient degree` (`test_transcendental.cpp:355-367`) compare with `approx_big` at `1e-30` and `1e-40`, so they pass it.
