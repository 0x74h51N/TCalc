# Combinatorics

## 2026-11-16, master 026ef26: the nPr and nCr loops against a Gamma closed form (#248)

`permute` and `choose` (`calc/combinatorics.cpp`) loop once per unit of `b` (nPr) or of $r = \min(b, a-b)$ (nCr), with no deadline (#248). Measured with a scratch program linked to `libcalc_core.a` (Debug), against a `cpp_dec_float_100` run of the same loop as the reference; "digits" is $-\log_{10}$ of the relative error.

| Case | Loop | $\Gamma$ ratio (`tgamma`) | `exp` of `lgamma` difference |
|---|---|---|---|
| nPr(30,3) | 0.011 ms, exact | 0.26 ms, 67.9 | 0.56 ms, 48.1 |
| nPr(100,50) | 0.027 ms, 66.3 | 0.95 ms, 51.5 | 1.0 ms, 47.9 |
| nPr(1e18,3) | 0.003 ms, exact | `nan` ($\Gamma(a+1)$ overflows) | 1.1 ms, 46.0 |
| nPr(1000,1000) | 0.52 ms, 66.0 | 0.35 ms, 51.9 | 1.2 ms, 48.9 |
| nPr(1e6,1e6) | 516 ms, 66.5 | 0.47 ms, 49.9 | 1.1 ms, 43.6 |
| nCr(1000,500) | 2.0 ms, 66.5 | 1.2 ms, 50.1 | 1.3 ms, 47.1 |
| nCr(1e6,5e5) | 2030 ms, 61.2 | 1.4 ms, 49.9 | 1.4 ms, 45.2 |

- The loop costs about 0.5 µs per step for nPr and 4 µs for nCr (the division); the closed forms about 1 ms at any size.
- `tgamma` of a ratio fails once $\Gamma(a+1)$ passes BigReal's range (`max_exponent10` is $2.88 \times 10^{17}$), even when the result fits: nPr(1e18,3) is `nan`. The `lgamma` difference has no such limit and keeps 41 to 48 digits even at $a$ = INT64_MAX ($b$ = 2000 and 100000), where the two `lgamma` values are close and large.
- Rejected: both hand-built forms need a size threshold beside them (the loop for small $b$), and neither is exact on its own.
- A result past BigReal's range is shown as `inf` today: `Γ(9223372036854775807)` and `10^{10^{18}}` on the app's path.

## 2026-11-16, master 026ef26: Boost's own ratio functions (#248)

Boost 1.83 already has the closed forms, and they avoid the overflow by computing the ratio directly instead of two $\Gamma$ values. `falling_factorial` (`boost/math/special_functions/factorials.hpp`) reduces $a(a-1)\cdots(a-b+1)$ to `tgamma_delta_ratio(a + 1, -b)`, and `binomial_coefficient` (`binomial.hpp`) computes $\binom{n}{k}$ as $1 / (k \cdot B(k, n-k+1))$ for large $n$ and rounds to the nearest integer (`ceil(result - 0.5)`). Their own signatures take `unsigned` (32 bits), so they are called through `tgamma_delta_ratio` and `beta` with BigReal arguments. For a type with no Lanczos approximation (BigReal), `tgamma_delta_ratio` shifts both arguments up to where Stirling's series holds and scales back.

Same scratch program, nPr as `round(tgamma_delta_ratio(a + 1, -b))`, nCr as `round(1 / (k * beta(k, a - k + 1)))` with $k = \min(b, a-b)$:

| Case | Time | Digits |
|---|---|---|
| nPr(5,2), nPr(30,30), nPr(1e18,3) | 0.01 to 0.28 ms | exact |
| nPr(100,50) | 0.77 ms | 50.4 |
| nPr(1e6,1e6) | 0.34 ms | 50.3 |
| nPr(INT64_MAX,2000) | 0.23 ms | 45.3 |
| nCr(5,2), nCr(1e18,2) | 0.28 to 0.70 ms | exact |
| nCr(50,25), nCr(100,50) | 0.4 ms | exact (118 digits) |
| nCr(1e6,5e5) | 1.0 ms | 49.8 |
| nPr(1e11,1e11) | 0.49 ms | `3.74893e+1056570551815` |
| nCr(INT64_MAX, INT64_MAX/2) | 1.0 ms | `inf` |
| nPr(INT64_MAX, INT64_MAX) | | throws `std::overflow_error` (not a `CalculatorError`) |

One call per op, no size threshold, exact where the result is an integer BigReal can hold, about 50 digits past that, under 1.1 ms at any size.

With Boost's overflow policy `policy<overflow_error<ignore_error>>` on the call, `tgamma_delta_ratio` returns `inf` instead of throwing: `nPr(INT64_MAX, INT64_MAX)` and `nPr(INT64_MAX, INT64_MAX/2)` are `inf`, `nPr(30,30)` and `nPr(1e11,1e11)` unchanged.

## 2026-11-16, master 026ef26: exactness of the closed form against today's loop

Every pair $0 \le b \le a \le 175$ for nCr and $a \le 60$ for nPr, closed form `round(...)` against `Calculator::choose` / `permute`, compared with `==` on BigReal (scratch `comb_exact.cpp`):

- The closed form is an exact integer in every pair, nPr and nCr.
- Today's nCr loop is not: 14535 of 15576 results carry noise in the guard digits past the 50 shown (`res /= i`), so `choose(6,3) == 20` is false today. Printed at 60 digits the values agree.
- nPr agrees exactly up to `nPr(55,43)`; from `nPr(55,44)` (about $3 \times 10^{65}$, past 50 digits) the two differ in the guard digits only.
- The app shows 16 significant digits (`nPr(40,40)` is `8.159152832478977e+47`), so none of this is visible in a result.

## 2026-11-16, fix/combinatorics-closed-form 5a7053f: nCr's last digit from 48 digits up

Every $0 \le b \le a \le 400$ with an exact result of at most 50 digits (35262 pairs), `Calculator::choose` against Python's `math.comb` (scratch `ncr_dump.cpp`):

- 1132 are one unit off in the last digit: 4 of 48 digits, 418 of 49, 710 of 50. None up to 47 digits. `nCr(176,60)` is `...064799`, exact `...064800`; through the app `nCr(176,60)-700938637298704280812242467451564851471559064800` is `-1`. Today's loop gives `-9.8e-23` there (also not 0, but not a whole unit).
- Cause: `beta` in BigReal is accurate to about $10^{-48}$ relative, so from about $10^{47}$ up the error passes 0.5 and `round` takes the neighbor.
- nPr: no error up to 50 digits (`a <= 400`, `b <= 40`).
- `beta` in `cpp_dec_float<100, std::int64_t>`, rounded, then converted to BigReal: 0 of 35262 wrong; `nCr(1000000,500000)` 0.09 ms against 1.4 ms in BigReal (`-O2`, scratch `ncr100.cpp`). With `cpp_dec_float_100` (32-bit exponent) `nCr(100000000000,50000000000)` wrongly becomes `inf`, so the exponent type must stay 64-bit as BigReal's.
- Applied (`choose` through `calc_detail::WideReal`): `ncr_dump.cpp` on the real `Calculator` gives 0 of 35262 nCr and 0 nPr wrong; `nCr(176,60)-700938637298704280812242467451564851471559064800` is `0` through the app.
