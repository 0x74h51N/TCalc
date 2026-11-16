# nPr and nCr in closed form, with no loop that can freeze the app

Issue #248, milestone First release. Measurements: [combinatorics.md](../findings/combinatorics.md).

## The bug

`nPr(9223372036854775807,9223372036854775807)` and `nCr(100000000000,50000000000)` never return: the app stops answering and has to be killed. `permute` and `choose` (`calc/combinatorics.cpp`) loop once per unit of $b$ (nPr) or of $\min(b, a-b)$ (nCr), about 0.5 µs and 4 µs a step, and the evaluation deadline (`check_deadline()`) lives in `eval`, which a `calc` kernel never reaches. `nCr(1000000,500000)` already takes 2 s. No other kernel has a loop that grows with its argument (`calc/*.cpp`; the `pow` loops are logarithmic), and the two smoke runs over every op find this freeze and no other (#250, pinned to #248).

## Approaches

- Carry the deadline into the kernels: the loop stops at 500 ms and shows the timeout, but a large input never gets an answer, and `calc` takes a dependency on `eval`. Rejected.
- A hand-built closed form, two `tgamma` values divided or the `exp` of an `lgamma` difference: needs the loop beside it for small $b$, `tgamma` turns `nPr(1e18,3)` into `nan`, and `lgamma` keeps only 41 to 48 digits. Rejected (findings).
- Boost's own ratio functions (chosen): one call per op at every size, exact where the result is an integer BigReal holds, about 50 digits past that, under 1.1 ms (findings).

## The fix

### nPr

$nPr(a, b) = a(a-1)\cdots(a-b+1) = \Gamma(a+1) / \Gamma(a-b+1)$, computed as `tgamma_delta_ratio(a + 1, -b)` in BigReal (`boost/math/special_functions/gamma.hpp`, already included in `combinatorics.cpp` for `fact` and `gamma`), rounded to the nearest integer. This is the call Boost's `falling_factorial` makes for a positive argument (`factorials.hpp`); `falling_factorial` itself takes a 32-bit `unsigned` count, which an int64 $b$ does not fit, so the kernel makes the call itself. `tgamma_delta_ratio` computes the ratio directly (scaled Stirling terms for a type with no Lanczos approximation), so no $\Gamma$ value that would overflow on its own is formed.

### nCr

With $k = \min(b, a-b)$: $\binom{a}{b} = 1 / (k \cdot B(k, a-k+1))$, computed with `beta` (`beta.hpp`, a new include) in `calc_detail::WideReal`, `cpp_dec_float` with twice BigReal's digits and its 64-bit exponent (`calc/internal/helpers.hpp`), rounded to the nearest integer and converted to BigReal, as Boost's `binomial_coefficient` does for large $n$ (`binomial.hpp`); `binomial_coefficient` itself takes 32-bit `unsigned` arguments. $k = 0$ is 1, as there.

### What stays

- `nonneg_or_zero`: a negative operand is the domain error it is today, and $b > a$ is 0.
- The signatures (`BigReal permute(long long, long long)`, `BigReal choose(long long, long long)`), the ops table rows and the coerce rules.
- Rounding: both results are integers by definition, so the closed form is rounded to the nearest integer. In BigReal, `beta` is accurate to about $10^{-48}$ relative, so from about $10^{47}$ up `round` took the neighbor (`nCr(176,60)` ended `...064799`, exact `...064800`); in `WideReal` all 35262 nCr of at most 50 digits with $a \le 400$ are exact, against `math.comb` (findings). nPr in BigReal had no such error and stays there.

### A result past BigReal's range

BigReal's largest exponent is about $2.88 \times 10^{17}$ (`max_exponent10`). A result past it is `inf`, as `Γ(9223372036854775807)` and `1e308^{1e308}` are today; the human agent chose `inf` over an error.

- nCr: `beta` comes back 0 and $1 / (k \cdot 0)$ is `inf` with no further code (`nCr(9223372036854775807,4611686018427387903)`).
- nPr: by default `tgamma_delta_ratio` throws `std::overflow_error`, which is no `CalculatorError`. The call takes Boost's documented overflow policy, `policy<overflow_error<ignore_error>>`, under which it returns `inf` itself. No other call in the native code passes a policy, so this is the first; it is the alias `calc_detail::InfOnOverflow` in `calc/internal/helpers.hpp` (measured: `nPr(9223372036854775807,9223372036854775807)` is `inf`). No `catch`, no new message or error kind.

Today both inputs freeze. A note beside such an `inf` saying the value is past BigReal's range is not needed for this fix and is not in it.

## Not in this spec

- A deadline inside kernels: with the loops gone no kernel has a loop that grows with its argument.
- Results past BigReal's range shown as `inf` by other ops (`Γ(9223372036854775807)`, `1e308^{1e308}`): the human agent keeps that as it is.
- A note explaining an `inf` past BigReal's range.

## Tests

- Native, `tests/unit/test_combinatorics.cpp`. `permute` and `choose` share one signature, so their rows go into one typed table (`tests.md`): the function is a member pointer in the row, the id says which (`"choose :: exact mid"`), input `a`, `b`, `expected` as text, `tol` (relative; null is exact equality). The existing `permute :: basic`, `choose :: basic` and out-of-range cases become rows of it; the two `domain throws` cases stay single. Rows:
  - exact: `permute(5,2)` 20, `choose(5,2)` 10, `permute(30,30)` $30!$, `permute(1000000000000000000,3)`, `choose(60,30)` 118264581564861424, `choose(100,50)`, `choose(176,60)` 700938637298704280812242467451564851471559064800 (48 digits);
  - to a 45-digit `tol` against a 100-digit reference: `permute(1000000,1000000)`, `choose(1000000,500000)`;
  - `inf`: `permute(9223372036854775807,9223372036854775807)`, `choose(9223372036854775807,4611686018427387903)`.
- Python: `nCr(5,2)` and `nPr(5,2)` in `tests/py/e2e/test_reductions_e2e.py` stay as they are and stay green.
- The freeze itself: the pinned smoke cases (`nPr :: i64 MAX, i64 MAX` in `smoke_stress.cpp`, `nPr(9223372036854775807,9223372036854775807)` in `tests/py/smoke/test_smoke.py`) are the red; with the fix they pass, the pin check turns them red, and removing the pins turns the runs green.
