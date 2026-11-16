# Native abort

## 2026-11-16, master 552eb93: what can end the process, and the int64 conversions next to it (#246, #247)

An assertion in libstdc++ calls `abort()`. It is not a C++ exception, so pybind11 and the error path (`CalculatorError` to `ErrorKind`) never see it. libstdc++ 15 asserts in an unoptimized build (`make native-build`, `NATIVE_BUILD_TYPE ?= Debug`); a Release build compiles the check out and goes on with undefined behavior. The native core itself has no `assert`, `BOOST_ASSERT`, `std::terminate` or `std::abort` (`grep -rnE` over `src/native/lib`).

The one abort seen: `to_integer` (`calc/number_theory.cpp:18`) checks only `int_like`, and `std::llround` of a double past int64 gives INT64_MIN on x86-64; `std::gcd` and `std::lcm` assert on its absolute value. Through the app path in Debug, `gcd(1e19,3)`, `gcd(2^{63},2)` and `lcm(10^{19},3)` abort. Release of f1777e0: `gcd(1e19,10)` is `2`, `lcm(10^{19},3)` is `-9223372036854775808`. `gcd(10000000000000000000,3)` (a BigReal) is the math error `gcd is only defined for integers`.

No double is needed: the exact INT64_MIN aborts too. `-9223372036854775807-1` is `Rational -9.223372036854775808e+18`; `gcd(-9223372036854775807-1,2)` and `lcm(-9223372036854775807-1,1)` abort in Debug, and `gcd(-9223372036854775807-1)` alone (no `std::gcd` call) is `-9.223372036854775808e+18`, a negative gcd.

Every `std::gcd`, `std::lcm`, `llround` and int64 cast in `src/native/lib`, read one by one:

- `calc/internal/helpers.hpp:209` (`rational_div_overflows`) and `eval/closed_forms.cpp:932`: `std::gcd` on values that cannot be INT64_MIN (the first guards it, the second takes positive denominators).
- `calc/arithmetic.cpp:61`, `intdiv(double, double)`: `static_cast<long long>(a / b)` with no range check. Debug, no abort: `intdiv(1e19,1)` and `intdiv(1e300,1)` are `-9.223372036854775808e+18`.
- `calc/statistic.cpp:213`, the int64 `sum`: an `__int128` total cast back to int64 with no range check. `sum(9223372036854775807,1)` is `-9.223372036854775808e+18`, `sum(9223372036854775807,9223372036854775807)` is `-2`. `mean` and `median` of the same are right (`9.2233720368547758e+18`).
- The BigInt `convert_to<std::int64_t>` in `closed_forms.cpp` and `literal.cpp` are each behind a range check.

No abort and a right answer for: `-(-9223372036854775807-1)`, `(-9223372036854775807-1)/(-1)`, `mod(-9223372036854775807-1,-1)`, `nCr(1e19,2)` (math error), `min(1e19)`.

## 2026-11-16, master 552eb93: how the abort got in

- 7a24f7f (2026-04-08): `Calculator::gcd(long long, long long)` and `lcm` call `std::gcd` and `std::lcm` straight; the binding takes integers, so a double cannot reach them.
- 7a7febb (2026-06-17): gcd and lcm become variadic folds over a Collection. `to_integer` is added to read each item, and it accepts a whole double through `std::llround` with no range check. This is where a double past int64 first reaches `std::gcd`.
- 3b57a06 (2026-08-12): the same abort is met on the exact trig path (`sin(-9223372036854775807-1)`, INT64_MIN into `std::gcd`) and fixed there, in `rational_div_overflows`, with the test row `an INT64_MIN numerator declines, not aborts`. The other `std::gcd` and `std::lcm` callers were not looked at.
- `tests/smoke/smoke_stress.cpp` (12ba95d, last changed 9637007 in 2025-12) calls double, BigReal and BigComplex kernels with inf and nan and allows only a `CalculatorError`. It predates the variadic gcd and has no number theory, int64 edge or collection row; CI builds Debug and runs it, so one `gcd` row past int64 would have aborted the run.
- The libstdc++ assertion fires without `_GLIBCXX_ASSERTIONS` in an unoptimized build (g++ 15.3.1: `-O0` aborts, `-O2` returns, on a two-line `std::gcd(llround(1e19), 3)` program).

## 2026-11-16, master 552eb93: inputs that never return

Run through the app path under `timeout -s KILL 8`: `nPr(9223372036854775807,9223372036854775807)` and `nCr(9223372036854775807,4611686018427387903)` are killed (exit 137), with no result after 8 s. `permute` and `choose` (`calc/combinatorics.cpp:57`, `:70`) loop once per unit of `b`. `nPr(10^{9},10^{9})` returns at once (math error, its operands are not Int64). With the app's budget (`EVAL_TIME_BUDGET_MS`, 500, in `app.py`) the same inputs, and `nPr(100000000000,100000000000)` and `nCr(100000000000,50000000000)`, are still killed after 8 s: `check_deadline()` runs only in the `iterate()` loop (`eval.cpp:871`) and the closed-form squaring loops (`closed_forms.cpp:829`, `:1287`), and a kernel loop in `calc` never reaches it (#248). A timed-out evaluation shows `kEvalTimedOut`, whose text is `Undefined` (`error_messages.hpp:127`).

## The native smoke run over apply (2026-11-16, fix/native-abort, Debug)

`./src/native/build/native/native_tests`, the `ops ::` cases of `smoke stress`: the suite has 11,613 cases (11,584 of them the sweep, one per `apply` call) and runs in about 1.2 s. Before the fix 166 failed, listed below.

- gcd: 78 aborts, lcm: 78 aborts (signal 6), all through `to_integer`. A mixed list aborts too: in `[INT64_MAX, 0.0]` the Int64 is read as a double, which rounds to $2^{63}$; `gcd(9223372036854775807,1e-320)` aborts the app the same way.
- nPr of INT64_MAX with INT64_MAX freezes (#248, pinned).
- `^` of INT64_MIN and -1, `⁻¹` of INT64_MIN, and `⌄` with INT64_MIN as the degree (7 cases) or as the radicand of degree -1 throw `boost::bad_rational` ("non-zero singular denominator"), which is no `CalculatorError`. No abort: the controller's catch-all (`controller.py:308`) shows "Invalid inputs". `(-9223372036854775807-1)^{-1}` reaches it from the editor. Cause: the exact `pow` (negative exponent) and `root` turn a value over with `boost::rational(den, num)`, whose constructor throws when the numerator is INT64_MIN; `add`, `sub`, `mul`, `div` go through `widen`/`narrow` and raise a math error instead. Issue #249, the 10 cases pinned to it.

## A core dump reads as a freeze (2026-11-16)

`core_pattern` here is `|/usr/lib/systemd/systemd-coredump ...`. Linux ignores `RLIMIT_CORE = 0` for a pipe, so each abort in a forked child still dumps; under load the dump took longer than the 1000 ms case limit and 3 to 7 lcm aborts were recorded as freezes, a different number each run. With `RLIMIT_CORE = 1` (the kernel skips a pipe dump on 1, and a file dump needs more than one byte) the run gives 78 and 78 aborts, no freeze, on two runs, and the whole native test run fell from 19 s to 2.4 s.

## The Python smoke run (2026-11-16, fix/native-abort at 60e8f38, Debug)

`make py-smoke`: 10,880 cases (every op of `op_table()` with a method, and the LaTeX forms, over the spec's 20 operand texts) on the app's path with the 500 ms budget, 16 workers, about 10 s. Before the pins: 17 failed, 16 `ValueError('bad rational: non-zero singular denominator')` (#249: `^`, `⁻¹`, `⌄` and `\root` with INT64_MIN) and `nPr(9223372036854775807,9223372036854775807)` frozen (#248). No abort: the gcd and lcm aborts were fixed by 60e8f38. `nCr` of the same pair returns within the limit.

A frozen case is caught in the worker by `faulthandler.dump_traceback_later(exit=True)`, whose C thread fires while a native call holds the GIL and exits with 1; an abort ends the worker with a negative return code.
