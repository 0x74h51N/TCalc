# Result text

## 2026-11-22: where the result line lost digits (#244, #235, #255), master 6f73f68

The display and the default text of a case, end to end (`tokenize`, `evaluate_branch`, `format_result`):

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=.:src:tests/py/e2e .venv/bin/python -c '
from test_eval_e2e import _eval
from tcalc.ui.controller.utils import format_result
for t in ["9007199254740993/2", "1/10000000", "2/3", "1e10", "1e-7", "1e400i", "10000000000"]:
    v = _eval(t); print(t, type(v).__name__, repr(format_result(v, group=True)), repr(format_result(v)))'
```

On master:

- A `Rational` was written through `to_double()`: `9007199254740993/2` showed `4.5035996273704960e+15` (exact `4503599627370496.5`), `1/10000000` showed `9.9999999999999995e-08`, `2/3` showed `0.6666666666666666`.
- A double past `1e10` was written with `.16e`, 17 digits padded with zeros: `1e10` showed `1.0000000000000000e+10`, and the 17th digit of `1e-7` showed its noise.
- A `BigReal` and a `BigComplex` were written by their binding at 16 of their 50 digits (`kPythonPrecision`), and a BigComplex kept its zero part (`0+1e+400i`).
- MR and `=` wrote the same 16-digit text into the expression: `1/3`, MS, MR, `*3-1` gave `-9.9999999999999998e-17`.
- A literal of more than 19 significant digits (`4503599627370496.4845789`) is read as a double before any formatting (#264).

## 2026-11-22: what writes exact text without a double

Boost's `str(digits)` on the 50-digit `BigReal` from `to_big` rounds to that many significant digits, drops trailing zeros and switches to the scientific form once the exponent passes the digits. Written with the count of its significant digits (trailing zeros dropped), a value whose rounded text is past `1e10` turns its zeros into the exponent: `10000000000` is `1e+10`, `12345678900` is `1.23456789e+10`, `12345678901` stays full. The threshold reads the rounded text, not the value: `9999999999.999999999999` writes as `1e+10`. The `decimal_text` rows in `src/native/tests/unit/test_eval.cpp` pin these:

```bash
make native-test
```

At 16 digits `4503599627370496.5` rounds to `4503599627370496`; at 20 it keeps its `.5`, and `1/3` shows twenty 3s.

## 2026-11-22: a BigReal promoted from a double showed the double's error past 16 digits

At 20 digits a BigReal that came out of a double overflow shows the double's binary value: `1e308*10` is `1.000000000000000011e+309`, `1e200*1e200` is `9.9999999999999993947e+399`. The literal `1e308` is a double, `1.00000000000000001097e308`, and `to_big(double)` widens it exactly. Master's 16 digits hid it. `to_big(double)` and `to_big_complex(Complex)` now widen through the double's shortest decimal (`std::to_chars`): `1e308*10` is `1e+309`, `1.5e308*1.5` is `2.25e+308`, `1e200*1e200` is `1e+400`, `1e200i*1e200i` is `-1e+400`, and a computed double keeps every digit it carries (`sqrt(2)*1e308*10` is `1.4142135623730951e+309`). The rows are in `FORMAT_CASES` (`tests/py/e2e/ui/test_format_result_e2e.py`). Widening a double near `1e300` cost about 1200 ns from its binary value and about 190 ns through its shortest decimal (200000 calls, `-O2`, a C++ probe of `BigReal(d)` against `tcalc::to_big(d)`).

## 2026-11-22: a repeating decimal with a line (#282)

The period of `p/q` is the order of 10 modulo $q$ with its factors 2 and 5 removed: 1 digit for 3, 6 for 7, 96 for 97, 554 for 9973, 999982 for 999983, 195225786 for 2147483647.

```bash
python3 -c '
def period(q):
    while q % 2 == 0: q //= 2
    while q % 5 == 0: q //= 5
    if q == 1: return 0
    r, k = 10 % q, 1
    while r != 1: r = r * 10 % q; k += 1
    return k
print([period(q) for q in (3, 7, 97, 9973, 999983, 2147483647)])'
```

A line-over decimal reads back exactly: integer part plus $\frac{\text{all decimal digits} - \text{non-repeating digits}}{10^n (10^k - 1)}$ (`0.16̄` is `1/6`, `12.50̄1̄2̄3̄` is `208333/16665`), with $n + k \le 18$ for an int64 denominator.
