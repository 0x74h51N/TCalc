# Result text: exact values shown from their own digits (#244, #235, #255)

Milestone: none of the open ones fits (the three issues have none); none proposed.

## What is wrong today

Measured on master 6f73f68 through `tokenize`, `evaluate_branch` and `format_result(..., group=True)`.

| Issue | Input | Type | Shown today | Exact value |
|---|---|---|---|---|
| #244 | 10000000000 | int | 1.0000000000000000e+10 | 10000000000 |
| #244 | 12345678901 | int | 1.2345678901000000e+10 | 12345678901 |
| #244 | 100000000000.5 | Rational | 1.0000000000050000e+11 | 100000000000.5 |
| #244 | 1e10 | double | 1.0000000000000000e+10 | 1e10 |
| #244 | 1e-7 | double | 9.9999999999999995e-08 | 1e-07 (nearest double) |
| #235 | 9007199254740993/2 | Rational | 4.5035996273704960e+15 | 4503599627370496.5 |
| #235 | 2/3 | Rational | 0.6666666666666666 | 0.666... |
| #235 | 1/7 | Rational | 0.1428571428571428 | 0.142857142857... |
| #235 | 1/10000000 | Rational | 9.9999999999999995e-08 | 1e-07 |
| #235 | 0.30000000000000004 | Rational | 0.3 | 0.30000000000000004 |
| #235 | 9223372036854775807/3 | Rational | 3.0744573456182584e+18 | 3074457345618258602.33... |
| | 2^{63} | BigReal | 9.223372036854776e+18 | 9223372036854775808 |
| #255 | 1e400i | BigComplex | 0+1e+400i | 1e+400i |
| #255 | 1e400i-1e400i | BigComplex | 0+0i | 0 |

A Rational is turned into a double before it is written (`to_double()`, `utils.py:75`); a BigReal or a BigComplex is written by its binding at 16 digits (`kPythonPrecision`, `bindings.hpp:31`) although it holds 50; a double past `1e10` is written with `.16e`, 17 digits padded with zeros (`utils.py:85-86`).

#235, the recall: `1/3`, MS, MR, `*3-1` is `-9.9999999999999998e-17`, exact `0`. Memory holds the exact `Rational` (`controller.py:186-187`); MR (`controller.py:181`) and `=` (`controller.py:164`) write `format_result(value)` into the expression, today `0.3333333333333333`.

#244's Expected column is replaced by the human agent's decision: a number is abbreviated only when its digits end in zeros (`10000000000` is `1e+10`), and `12345678901`, `2^{40}` and `9007199254740993` are shown in full.

## Design

### Native: `decimal_text`

`tcalc::decimal_text(value, digits)` in `src/native/lib/value.hpp`, beside `to_big`, writes an exact value as decimal text, one overload per arm:

- int64, Rational, BigReal: `to_big(value).str(digits)`. Boost rounds to that many significant digits, drops trailing zeros and writes the scientific form only when the exponent is past the digits. When that rounded text is `1e10` or more (a named `constexpr`; the text, not the value, so `10^{10}-1/10^{12}` is `1e+10` too), the digits before the `e` of that text, trailing zeros dropped, are counted and the value is written with that count, so `10000000000` is `1e+10`, `12345678900` is `1.23456789e+10` and `12345678901` stays `12345678901`.
- BigComplex: each part through `BigReal(c.real())` and `BigReal(c.imag())` and the BigReal overload; a part that is zero is dropped (#255), `0` when both are: `1e+400i`, `-1e+800`, `1234+3.3333333333333333333e+199i`.

A double that overflows into a BigReal or a BigComplex is widened through its shortest decimal (`std::to_chars`) in `to_big(double)` and `to_big_complex(Complex)`, not through its binary value: at 20 digits the binary value of the literal `1e308` shows `1e308*10` as `1.000000000000000011e+309`; through its shortest decimal it is `1e+309`, and a computed double keeps every digit it carries.

It is bound in `bind_eval.cpp` (after the number types) with `py::arg("value"), py::arg("digits")`, and tested in `src/native/tests/unit/test_eval.cpp` beside `to_big`'s tests. A value is formatted only when it is shown: `evaluate` keeps returning the value, which the fraction view, memory, M+, #282 and #275 need, and a digits setting (#128) re-formats without evaluating again. The bindings' `__str__` stay as they are, the debug form.

### Python: `format_result`

- `digits` is 20, one named constant in `utils.py`; #128 makes it a setting, up to 50, BigReal's digits. A double keeps 16: it holds no more.
- Display (`group=True`): an `int`, a `Rational`, a `BigReal` and a `BigComplex` are `calc_native.decimal_text(value, RESULT_DIGITS)`. A double past `1e10` or under `1e-6` is written with 16 significant digits (`.15e`), trailing zeros dropped: `1e+10`, `1.414213562373095e+12`, `1e-07`; an infinite double (`cosh(1000)`) is `inf`, as before. `to_double()` and `_fmt_exact_int` go away.
- Every display text goes through one new helper, which replaces the grouping lines of `fmt_real` (`utils.py:95-98`): it puts thousands separators into every integer digit run and leaves the exponent alone, so both parts of a complex number are grouped (`1,234+3.3333333333333333333e+199i`, `12,345+12,345.5i`). The exponent keeps the form Python and Boost write, with its sign and two digits at least (`1e+10`, `1e-07`), as the human agent chose.
- Default (MR, `=`, collection items), text that reads back as the same value: an `int` and a `Rational` with denominator 1 are `str(n)` (`10000000000`); a `Rational` fraction is `f"({value})"` from `bind_rational.cpp:40` (`(1/3)`; the parentheses keep `2^(1/3)` one power). A `BigReal` and a `BigComplex` are `decimal_text` at 20 digits, which does not keep all 50. The controller does not change.

## Cases

Display, the native digits measured with a C++ probe of `to_big(...).str(digits)` and the count step, the double and the helper with Python probes:

| Input | Display text |
|---|---|
| 1/3 | 0.33333333333333333333 |
| 2/3 | 0.66666666666666666667 |
| -2/7 | -0.28571428571428571429 |
| 9007199254740993/2 | 4,503,599,627,370,496.5 |
| 0.30000000000000004 | 0.30000000000000004 |
| 1/10000 | 0.0001 |
| 1/30000 | 3.3333333333333333333e-05 |
| 1/10000000 | 1e-07 |
| 9223372036854775807/3 | 3,074,457,345,618,258,602.3 |
| 100000000000.5 | 100,000,000,000.5 |
| 10000000000 | 1e+10 |
| -10000000000 | -1e+10 |
| 12345678900 | 1.23456789e+10 |
| 12345678901 | 12,345,678,901 |
| 2^{40} | 1,099,511,627,776 |
| 9999999999 | 9,999,999,999 |
| 2^{63} | 9,223,372,036,854,775,808 |
| 1e400/3 | 3.3333333333333333333e+399 |
| 1e10 | 1e+10 |
| 2^{0.5}\*1e12 | 1.414213562373095e+12 |
| 1e-7 | 1e-07 |
| 1e400i | 1e+400i |
| 1e-400i | 1e-400i |
| 1e400i-1e400i | 0 |
| (1e400i)^{2} | -1e+800 |
| (-4e400)⌄(-2) | -5e-201i |
| sqrt(-1e400)/3+1234 | 1,234+3.3333333333333333333e+199i |
| 10^{10}-1/10^{12} | 1e+10 |
| cosh(1000) | inf |
| 1e308\*10 | 1e+309 |
| 1e200\*1e200 | 1e+400 |
| 1e200i\*1e200i | -1e+400 |
| sqrt(2)\*1e308\*10 | 1.4142135623730951e+309 |

Default: `10000000000`, `(1/3)`, `(9007199254740993/2)`, `10000000000000001`, `1e+400i`; each reads back to the same value (a Rational with denominator 1 may read back as `int`, the same number).

## Out of scope

- A double or a BigReal recalled through MR is not made exact; the human agent chose the `Rational` fix.
- A literal of more than 19 significant digits is read as a double (#264).
- The repeating decimal shown with a line (#282).
- Copy (Ctrl+C) keeps copying the display text.
