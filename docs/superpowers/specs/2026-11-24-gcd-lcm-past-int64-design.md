# gcd and lcm of an integer past int64

Issue #247, milestone 22 (First release). The history below was measured on 2026-11-25 in a Debug build, each case in its own process with `scripts/native_probe eval` (an abort ends the run). The case table was measured on 2026-11-26 through `tokenize`, `evaluate_branch` and `format_result`, on master 4f1ad15 (Release) and on this branch at 28c0ca7.

## The bug

The gcd and lcm kernel (`calc/number_theory.cpp`) works in int64: `to_integer` turns each item of the list into an `std::int64_t`, and the fold calls `std::gcd` and `std::lcm`.

- An operand past int64 is refused. The #250 guard (0eea466) throws `math_error()` for a whole double with `std::fabs(d) >= kInt64End` (`0x1p63`) and for `v == std::numeric_limits<std::int64_t>::min()`. `to_integer` has no BigReal arm, so every BigReal is `gcd is only defined for integers`, `2^62` included, a BigReal inside int64.
- An lcm whose operands fit int64 and whose result does not aborts a Debug build in `std::lcm` (`numeric:212`, `Assertion '!__overflow' failed`) and wraps in a Release build (`lcm(9223372036854775807,2)` is `-2`).
- A single negative operand comes back negative: `gcd(-5)` is `-5`.

## Why there is no BigReal arm

No commit, spec or finding chose to leave BigReal out; gcd never had the arm. BigReal was in the native core by 2025-12 (038b32d), before gcd.

- 7a24f7f (2026-04-08): gcd and lcm are `Calculator::gcd(long long, long long)`, a call to `std::gcd`. The binding takes integers.
- 7a7febb (2026-06-17): they become folds over a Collection. `to_integer` reads an Int64 and a whole double; its commit message names neither BigReal nor a range.
- 0eea466 (#250): the guard. Its plan leaves the right answer to this issue.
- The rational overflow fix (#245) retried a Rational result past int64 in BigReal instead of double, so `3^{40}` and `10^{19}+2` became BigReal and their gcd `only defined for integers`. No right answer was lost: before it, a Release build gave `gcd(3^{40},3^{39})` as `2048` (the issue's table), and a Debug build aborted on `gcd(3^{40},3)` (`rational-overflow.md`, 2026-11-16).

Nothing between the editor and the kernel stops a BigReal item: the call's arguments become a List through `collection_item` (`eval.cpp`), `coerce` returns a Collection operand untouched, the op row is `reduce(OpId::Gcd, ...)` with the one arm `Coll`, and a BigReal result returns through `to_value`, as `median`'s does. The kernel's signature does not change, so neither the arms nor the stubs do.

## Why the guard is there

Before #250, `to_integer` turned a whole double past int64 into INT64_MIN through `std::llround`, and passed INT64_MIN itself on. `std::gcd` and `std::lcm` take the absolute value, which int64 does not have for INT64_MIN: a Debug build aborted, a Release build gave a wrong number (`gcd(1e19,10)` was `2`). The error and the bug have one cause, the int64 kernel. A kernel that never takes an int64 absolute value needs no guard, so one change removes both.

## Approaches

- A. One arm on `boost::multiprecision::cpp_int`: every operand read into it. `gcd(12,8)` would allocate where it does not today.
- B. Two arms, chosen. Arm 1 keeps an int64 path with no allocation for the operands int64 holds; arm 2 takes the rest in `cpp_int`, with Boost's `gcd` and `lcm`. The exact trig fold is built the same way (`fold_half_turns`, `helpers.hpp`).
- C. A factored integer `r * 2^two * 5^five` with `r` an `int512_t`: built first (f68f447) and replaced. It kept `10^{400000}` small, but it was gcd and lcm written by hand where Boost has them, and its one gain went when a BigReal from $10^{72}$ became the multiprecision mode's (below).
- D. Euclid on BigReal with `fmod`: dropped. `cpp_dec_float` division comes out low on a division that is exact in integers (`3^{40}/3^{39}` is `2.99...98944`, not `3`), so the remainders are wrong.

## The kernel

### Arm 1: uint64

Arm 1 takes an Int64 item, and a double item that is `int_like(d)` with $|d| < 2^{53}$ (`small_magnitude`; a double holds every integer there, so `std::llround` is exact).

- Each operand is read as its `std::uint64_t` magnitude (`calc_detail::magnitude`), so INT64_MIN has one and nothing is negated in int64.
- gcd folds with `std::gcd`. lcm folds with `a / std::gcd(a, b) * b`, the product formed in `int256_t` and read back only when it fits, as `Calculator::mul` forms a Rational product. A zero operand makes the lcm 0.
- An operand arm 1 cannot read, or a step past `std::uint64_t`, hands the fold to arm 2, with `acc` and the items left.
- The result is an Int64 when it is at most `INT64_MAX`, else arm 2's conversion forms it (`gcd(-9223372036854775807-1)` is `9223372036854775808`).

### Arm 2: cpp_int

Every item is read by `calc_detail::int_operand`, one visit shared by the kernel's `CollectionItem` and the call rule's `Value`, onto the `whole_operand` overloads:

- Int64: its magnitude.
- double: below $2^{53}$ as arm 1 reads it; past it, if `int_like`, its shortest text (`to_big`), the value it shows: `1e23` is $10^{23}$, not the double's `99999999999999991611392`.
- BigReal: from $10^{72}$ (an infinity included) `needs multiprecision mode`. BigReal holds 73 digits, so a whole BigReal from $10^{72}$ may be a rounded integer, and a gcd of a rounded integer is a wrong number, not a rounded one (`2^{265}` is 80 digits and reaches gcd with its last 7 lost). Below it, a value that is not `whole` (exact, guard digits included) is `only defined for integers`, and a whole one is read through its scientific text into `cpp_int`.
- Rational (the call rule only): whole with denominator 1, else `only defined for integers`.
- Anything else (a complex, a nested collection): `only defined for integers`.

The fold is `mp::gcd` or `lcm_of`, which throws `needs multiprecision mode` when the lcm's msb passes `kMaxIntBits` (16384). The result is an Int64 when it fits, else a BigReal formed by `rounded_big` from the integer's leading 100 digits and its power of ten: BigReal reads no more of a text than that, and the whole text of a 16384-bit integer takes 0.8 ms against 0.02 ms (`-O2`). The direct construction from an integer is not used: `BigReal(int512_t)` was wrong from 74 digits on (`10^74` comes out different), measured for f68f447.

### The two error rules

The human agent's rules:

- An integer that exists but cannot be held exactly is `needs multiprecision mode` (#275): a BigReal from $10^{72}$, an lcm or an argument past 16384 bits.
- A value that is no integer at any precision is `only defined for integers`, also when it is past $10^{72}$: multiprecision mode could not answer it either.

## Powers and factorials read from their tokens

### Why

`2^{265}` is evaluated to a BigReal before gcd sees it, rounded to 73 digits. Nothing on the value side recovers the lost digits; a tolerance Euclid answers `gcd(2^{265},2^{264})` but gives `3` for `gcd(2^{265},3)`. The integer is still exact in the tokens: its base and exponent, or the n of a factorial.

### The call rule

- `exact::CallRule`, `std::optional<Value> (*)(OpId, std::span<const parser::ParenElement>, const Calculator &, Calculator::AngleUnit)`, an `ExactRow` field read only in `eval_call`, before `call_operands`. gcd and lcm carry `fold_rule<gcd_of, gcd_power>` and `fold_rule<lcm_of, lcm_power>`. A `TokenRule` takes one row and cannot carry a call of many arguments.
- The rule declines before evaluating anything when no argument is a power or a factorial, or an argument is empty: the kernel path then runs as before and reports the empty one.
- Otherwise it evaluates every argument itself, each once, and every argument before any is folded, as the dataset is before the kernel. An argument that evaluates to a collection is the dataset's error: the rule declines and the kernel path reports it, the arguments up to it evaluated again on the way to that error.
- An argument is read from its tokens when, without its parens and a leading minus (the magnitude drops it), it is one `LatexKind::Pow` token with two non-empty sides, or `x !`. A power with an empty side is not one: `2^{}` is `1`.
- A power: the Pow row's latex rule (`latex_rule`, `e^{ln u}` is `u`) first, as `eval_latex` does; then its base and exponent are evaluated once each.
  - A Rational base with denominator other than 1 and a positive integer exponent: no integer (`gcd(2.5^{1000},2)`).
  - An integer base and a fractional exponent $p/q$: an integer only when the base is a $q$-th power $r$ (`exact_int_root`), and then it is $r^p$ (`gcd(4^{600.5},6)` is `2`); otherwise no integer (`gcd(10^{400.5},2)`).
  - An integer base $m \ge 2$ and an exponent $e \ge 0$: $m^e$ in `cpp_int` when $e \log_2 m < 16385$, the msb bound the factorial and lcm read; past it the power is never built (`HugePower`).
  - Anything else: the value `apply(Pow)` gives, read as the kernel reads an item.
- A factorial: n evaluated once. A Rational n with denominator other than 1 is no integer (`gcd(200.5!,2)`); a whole $n \ge 0$ is the product $2 \cdots n$ while its msb stays within 16384 bits; anything else, a negative n included, is the value `apply(Fact)` gives.
- The fold: exact integers and values in argument order, a no-integer argument throwing `only defined for integers` in its place, then each `HugePower` last. gcd reads it with `powm` against the fold of the others, $\gcd(m^e, a) = \gcd(m^e \bmod a, a)$, so `gcd(2^{9223372036854775807},12)` is `4`; alone or beside 0 the gcd is $m^e$ itself, `needs multiprecision mode`. lcm of one is a multiple of it, `needs multiprecision mode`, unless another argument is 0.

### Forms the rule does not read

A power inside a larger argument (`gcd(2^{265}+0,3)`, `gcd(2*2^{264},3)`), the bracket form `gcd[2^{300},6]`, a list `gcd([2^{300},6])` and a variable holding a power are evaluated first, and a BigReal from $10^{72}$ is `needs multiprecision mode`. The evaluator has no big integer arm; keeping one through every op is #275.

## Cases

Master is 4f1ad15 in a Release build, which wraps where a Debug build aborts. A result is written as the result line shows it.

| Case | Expected | Master | This branch |
|---|---|---|---|
| gcd(1e19,10) | 10 | Math error | 10 |
| gcd(-1e19,5) | 5 | Math error | 5 |
| gcd(1e19,3) | 1 | Math error | 1 |
| lcm(10^{19},3) | 3e+19 | only defined for integers | 3e+19 |
| lcm(1e19,2) | 1e+19 | Math error | 1e+19 |
| gcd(10000000000000000000,3) | 1 | only defined for integers | 1 |
| gcd(10^{19}+2,3) | 3 | only defined for integers | 3 |
| gcd(10^{20}+5,15) | 15 | only defined for integers | 15 |
| gcd(3^{40},3^{39}) | 4052555153018976267 | only defined for integers | 4052555153018976267 |
| lcm(10^{19}+2,4) | 20000000000000000004 | only defined for integers | 20000000000000000004 |
| lcm(10^{12},10^{12}+1) | 1000000000001000000000000 | 2003765205206896640 | 1.000000000001e+24 |
| lcm(9223372036854775807,2) | 18446744073709551614 | -2 | 18446744073709551614 |
| lcm(2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53) | 32589158477190044730 | -4304329670229058502 | 3.258915847719004473e+19 |
| gcd(-9223372036854775807-1) | 9223372036854775808 | Math error | 9223372036854775808 |
| gcd(-9223372036854775807-1,2) | 2 | Math error | 2 |
| gcd(-9223372036854775807-1,0) | 9223372036854775808 | Math error | 9223372036854775808 |
| lcm(-9223372036854775807-1,1) | 9223372036854775808 | Math error | 9223372036854775808 |
| lcm(-9223372036854775807-1,0) | 0 | Math error | 0 |
| gcd(-5) | 5 | -5 | 5 |
| lcm(-5) | 5 | -5 | 5 |
| gcd(2^{62},4) | 4 | only defined for integers | 4 |
| gcd(2^{63}-1,2^{62}) | 1 | only defined for integers | 1 |
| gcd(12,10^{19}+2) | 6 | only defined for integers | 6 |
| gcd(0,10^{19}) | 1e+19 | only defined for integers | 1e+19 |
| lcm(0,10^{19}) | 0 | only defined for integers | 0 |
| gcd(-10^{19},4) | 4 | only defined for integers | 4 |
| gcd(√(10^{40}),3) | 1 | only defined for integers | 1 |
| gcd(1e23,10) | 10 | Math error | 10 |
| gcd(1e300,1e299) | 1e+299 | Math error | 1e+299 |
| gcd(10^{60}+1,10^{60}) | 1 | only defined for integers | 1 |
| lcm(10^{30}+1,10^{30}+3) | 1000000000000000000000000000004000000000000000000000000000003 | only defined for integers | 1e+60 |
| gcd(10^{400},3) | 1 | only defined for integers | 1 |
| gcd(2^{265},3) | 1 | only defined for integers | 1 |
| gcd(-2^{265},3) | 1 | only defined for integers | 1 |
| gcd(2^{265},2^{264}) | 2^264 | only defined for integers | 2.9642774844752946028e+79 |
| lcm(2^{265},2^{264}) | 2^265 | only defined for integers | 5.9285549689505892057e+79 |
| gcd(3^{200},3^{100}) | 3^100 | only defined for integers | 5.1537752073201133104e+47 |
| gcd(3^{400},3) | 3 | only defined for integers | 3 |
| gcd(100!,99!) | 99! | only defined for integers | 9.3326215443944152682e+155 |
| gcd(2^{9223372036854775807},12) | 4 | only defined for integers | 4 |
| gcd(4^{600.5},6) | 2 | only defined for integers | 2 |
| gcd(10^{80}+1,3) | needs multiprecision mode | only defined for integers | needs multiprecision mode |
| gcd(2^{265}+1,3) | needs multiprecision mode | only defined for integers | needs multiprecision mode |
| gcd(10^{400000},10^{399999}) | needs multiprecision mode | only defined for integers | needs multiprecision mode |
| lcm(2^{16384},3) | needs multiprecision mode | only defined for integers | needs multiprecision mode |
| gcd(2.5^{1000},2) | only defined for integers | only defined for integers | only defined for integers |
| gcd(10^{400.5},2) | only defined for integers | only defined for integers | only defined for integers |
| gcd(200.5!,2) | only defined for integers | only defined for integers | only defined for integers |
| gcd(10^{19}+1/2,3) | only defined for integers | only defined for integers | only defined for integers |
| gcd(10^{60}+1/2,3) | only defined for integers | only defined for integers | only defined for integers |
| gcd(1.5,2) | only defined for integers | only defined for integers | only defined for integers |
| gcd(1/2,3) | only defined for integers | only defined for integers | only defined for integers |
| gcd(i,2) | only defined for integers | only defined for integers | only defined for integers |
| gcd(3.0000000001,6) | only defined for integers | only defined for integers | only defined for integers |
| gcd((4,6)) | not defined for a point | not defined for a point | not defined for a point |
| gcd(1e18\*1.2345678901234567,100) | 4 | 4 | 4 |
| gcd(1.2345678901234567e18,100) | 100 | 100 | 100 |
| gcd(9.007199254740993e15,3) | 3 | 3 | 3 |
| gcd(12,8) | 4 | 4 | 4 |
| gcd(-12,8) | 4 | 4 | 4 |
| lcm(4,-6) | 12 | 12 | 12 |
| gcd(0,0) | 0 | 0 | 0 |
| gcd(-0,5) | 5 | 5 | 5 |
| lcm(3037000500,3037000499) | 9223372033963249500 | 9223372033963249500 | 9223372033963249500 |

Notes on the rows:

- A result past 20 significant digits is a BigReal, shown in the result line's form; its value holds 73 digits (`gcd(2^{265},2^{264})` to the last digit, `gcd(100!,99!)` within a relative `1.1e-76`).
- `gcd(1e18*1.2345678901234567,100)` stays `4`: `1e18` is a double, so the product rounds to `1234567890123456768` before gcd runs, the product's rounding, not gcd's. `10^{18}*1.2345678901234567` is a Rational and gives `100`.
- `gcd(10^{400000},10^{399999})`: both are powers past 16384 bits, so neither can be read against the other.

## Not in this spec

- `gcd(3^{40}/3^{39},6)` is `only defined for integers` on master and here; the right answer is `3`. The division leaves `2.99...98944` in BigReal's guard digits, which `whole` reads exactly: #288, with `fact`, `gamma`, `mod`, `intdiv`, `nCr` and `nPr`.
- `gcd(1e19+0.5,3)`: the sum is the double `1e19` before gcd reads it, the rounding of the addition.
- An Int64 lifted to double by the `Collection` constructor: `gcd(9007199254740993,3e0)` is `1`, the right answer `3`, since the list is `[9007199254740992.0, 3.0]` before gcd reads it. Every collection op reads that lift.
- A double lifted to BigReal by the constructor takes its binary value, while `to_big(double)` takes its shortest decimal; `gcd(1e23,10^{23})` reads `99999999999999991611392`.
- `...` in a list (`[1,...,5]` is `[1, 0, 5]`): #287.

## Cost

Release, `native_probe eval --time`, median ns of 20000 runs, three runs each.

- `gcd(12,8)`: 306 to 307 on master, 332 to 335 here; `lcm(4,6)`: 308 to 309 on master, 332 to 335 here.
- A power argument is cheaper than master's value path: `gcd(2^{10},6)` 741 to 756 on master, 554 to 564 here.
- Each argument is evaluated once: `gcd((\sum_{n=1}^{100000}gcd(n,6))^{8},2)` takes 62.4 ms, the power alone 62.9 ms.
- An lcm of 40 arguments up to the bound takes 1.0 ms; most of it is Boost's `cpp_int` division in each gcd step (about 19 µs for a 16000-bit by a 400-bit number, `-O2`).

## Tests

- Native, `src/native/tests/unit/test_number_theory.cpp`: one table for gcd and lcm, the kernel a member function pointer in the row, the operands a `std::vector<CollectionItem>`, the expected value a `CollectionItem` and a relative `tol`, exact on every row but the lcm of three operands past BigReal's digits (`10^70+1`, `10^70+3`, `10^70+7`), compared within `1e-72`. `EXPECT_THROWS` cases for a BigReal from $10^{72}$, an infinity and a BigReal fraction past 50 digits.
- e2e, `tests/py/e2e/test_eval_e2e.py`: an Int64 result in `test_native_eval_golden`; a BigReal result past BigReal's digits in `test_bigreal_close_results`, read with `calc_native.decimal_text(out, 100)` and compared within a relative `1e-72`, since `str()` of a BigReal shows 16 digits. Errors in `test_call_arg_errors` (`tests/py/e2e/test_reductions_e2e.py`).
- Every guard of the call rule has its row, shown red with the guard removed: an empty power side, a negative n, the log identity (`gcd(e^{ln(3^{50})},3)`), a collection beside a power, an empty argument, a whole Rational, the lcm bound, a leading minus, the bound for a power whose msb is 16384 (`lcm(19^{3857},1)`), and `gcd(2^{9223372036854775807},0)`, which without its guard ends the process in `powm` with SIGFPE.
- `make native-test` and `make py-smoke` green with no pin added.

## Probe tools

`native_probe boost` gained the rows `int_gcd`, `int_lcm`, `dec_order`, `dec_shift`, `whole` (`floor(x) == x`) and `int512` (the value through `int512_t` and back), and reads `--time`; an unknown NAME lists them. A row returns its value in the row's type, so `int512` shows the round trip, not the integer: the integer side was measured in a scratch program.
