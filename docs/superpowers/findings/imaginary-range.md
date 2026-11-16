# Imaginary range (#239)

## 2026-11-16, chore/type-safety-rules 39ec7ee: which promotion step loses the range

Every row is a real `evaluate`, run with:

```
PYTHONPATH=src .venv/bin/python -c "import calc_native as n; c=n.Calculator(); print(repr(n.evaluate(n.tokenize_string('1e-400i'), c, n.AngleUnit.RAD)))"
```

Two separate faults, the literal and the range promotion of the Cx arm. Operand promotion is not one of them.

### Two readers of `i`

Through the app's path (the editor's plain text, `tokenize`, `evaluate_branch`, `format_result`; `_eval` in `tests/py/e2e/test_eval_e2e.py`), `i` is read in two places:

- After a number (`3i`, `1e400i`, also `1e400 i`, which the editor writes back as `1e400i`) the tokenizer makes one NumberToken, and `literal_value` reads it.
- Anywhere else (`i`, `1e400*i`, the prefix `i1e400`) it is the ConstToken `i`, a `Complex(0, 1)` that `apply` multiplies with the number, so `coerce` decides the arm.

The same number gives two answers today: `1e400i` is `infi`, `i1e400` and `1e400*i` are `0+1e+400i`; `1e-400i` is `0`, `i1e-400` is `0+1e-400i`; `99999999999999999999i` is `1.0000000000000000e+20i`, `99999999999999999999*i` is `0+1e+20i`. For a Double or an Int64 the two readers agree: `9007199254740993i`, `9007199254740993*i` and `i9007199254740993` are all `9.0071992547409920e+15i`. The literal's own prefix branch (`i3` in `literal_cases`) is not reached from the app: the tokenizer makes `i3` a ConstToken and a NumberToken.

### The literal

`literal_value` (`literal.cpp`, the imaginary branch) reads the part before `i` with `parse_real` and narrows its Int64, Double or BigReal with `to_double` into `Complex(0, magnitude)`.

- `1e400i` is `infj`, `1e-400i` is `0j`, `9007199254740993i` is `9007199254740992j`.
- What follows only carries the damage: `1e400i-1e400i` is `nanj`, `1e400i*0` is `(nan+nanj)`, `1e400+1e400i` is `BigComplex("1e+400+infi")`.

### Operand promotion keeps the range, not an Int64's digits

`coerce` lifts a BigReal and a Complex to BigComplex, and the BigComplex arm keeps the range: `1e400*i`, `10^{400}i` are `BigComplex("0+1e+400i")`, `i*10^{-400}` is `BigComplex("0+1e-400i")`, `(10^{400}*i)^{2}` is `BigComplex("-1e+800+0i")`, `(10^{-400}i)*(10^{-400}i)` is `BigComplex("-1e-800+0i")`.

An Int64 past $2^{53}$ next to a Complex is lifted to Complex (`lift_to_complex`) and loses its last digits, with no literal involved: `9007199254740993*i` is `9007199254740992j`, `9007199254740993+i` is `(9007199254740992+1j)`. The literal `9007199254740993i` loses them the same way. The real `9007199254740993+0.5` stays an exact `Rational`, but next to a double the real arm narrows the same way: `9007199254740993+1e0` and `9007199254740993*1e0` are `9007199254740992.0`. The Int64 to Complex lift is that narrowing, not a fault of its own; only the literal, which has no other operand, picks a narrower arm than its value needs. A BigComplex holds an Int64 whole: `apply` Mul of `9223372036854775807` and `BigComplex("0", "1")`, minus `BigComplex("0", "9223372036854775806")`, is `0+1i`. `99999999999999999999i` is `1e+20j` while the real `99999999999999999999` is a `BigReal`.

### The Cx arm has no range promotion

With literals a double holds, the result of an op on the Cx arm leaves double's range and nothing widens it:

- `promote_range` (`eval.cpp`) returns at once when the result is not a `double`. Overflow: `1e200i*1e200i` is `(-inf+0j)`, `1e308i+1e308i` is `infj`, `e^{1000+i}` is `(inf+infj)`, `sin(1000i)` is `infj`, `\sqrt{1e300i*1e300}` is `(inf+infj)`, `(1e300+1e300i)*(1e300+1e300i)` is `(nan+infj)`, `(1e200i)/(1e-200)` is `(nan+infj)`. Underflow: `1e-200i*1e-200i` and `(1e-200+1e-200i)^{2}` are `0j`, `1e-160i*1e-160i` is the subnormal `(-1e-320+0j)`, and `1/(1e-200i*1e-200i)` is a Math error from the zero.
- `promote_big`, the rule that widens a power before it runs, returns when an operand is complex: `(2i)^{2000}` and `2i^{2000}` are `(inf-infj)`, `(2+i)^{1000}` is `(inf-infj)`. The real `2^{2000}` is widened.
- The BigComplex arm is there to widen into: `apply` on two `BigComplex("0+1e200i")` gives `-1e+400+0i` for Mul and `0+2e+200i` for Add.

Control: `(1+i)^{2000}` is `(1.0715086071862673e+301+0j)`, correct and in range.

### The BigComplex arm answers every row

`apply` on the same operands as `BigComplex` (`n.apply(c, n.OpId.Mul, [n.BigComplex("0", "1e200"), n.BigComplex("0", "1e200")], n.AngleUnit.RAD)`) gives the right value where the Cx arm fails: Mul `-1e+400+0i`, `-1e-400+0i` and `-1e-320+0i`; `(1e300+1e300i)^2` as Mul `0+2e+600i`; Div `0+1e+400i`; Pow `(2i)^{2000}` `1.148130695274255e+602+0i`; Exp `(1000+i)` `1.064433965627625e+434+1.657757680453514e+434i`; Sin `(1000i)` `0+9.850355570085235e+433i`.

- Every overflowed Cx row has a part that is `inf`; the `nan` parts only come with one. `1e400i*0`, the only `nan+nanj`, has an `inf` operand from the literal.
- `(2i)^{2000}` overflows to `inf` after the kernel, so a check after the kernel catches it without `promote_big`. `promote_big` exists for the power that lands in range but inexact: real `10^{308}` is a `BigReal`, `(10i)^{308}` is the double `(1e+308+0j)`, which prints the same.
- The Cx arm agrees with BigComplex where it keeps its range: `(1e300+1e300i)/(1e300+1e300i)` is `(1+0j)`, `i*i` is `(-1+0j)`.
- A part can fall to zero while the other part holds the magnitude: `(1+1e-200i)*1e-200` is `(1e-200+0j)`, BigComplex `1e-200+1e-400i`. A zero test on the whole value does not see it.

### `e^{z}` reads `e` as a double (#241)

`e^{1000+i}` is a Pow LatexToken with the double `e` as its base. Pow of `BigComplex("2.718281828459045", "0")` and `BigComplex("1000", "1")` is `1.064433965627533e+434+1.657757680453371e+434i`; Exp of `BigComplex("1000", "1")` is `1.064433965627625e+434+1.657757680453514e+434i`, and the exact value is `1.06443396562762528e+434+1.65775768045351430e+434i` (mpmath, 30 digits). The real arm today: `e^{1000}` is `1.970071114016942e+434`, `exp(1000)` is `1.970071114017047e+434`.

## 2026-11-16, fix/imaginary-range 82d887f: after the fix

The literal gives a BigReal magnitude as a BigComplex (6882b68), and `promote_range` widens a Complex result into BigComplex (82d887f). `make native-test`: `1397 PASSED`; `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e --ignore=tests/py/e2e/ui -q`: `481 passed`. The new rows, run on f1777e0 by the review: native `10 FAILED`, e2e `9 failed`, all of them bug rows.

- Through the app path: `1e400i`, `i1e400` and `1e400*i` are `0+1e+400i`; `1e-400i` is `0+1e-400i`; `1e200i*1e200i` is `-9.999999999999999e+399+0i`, the digits of the double `1e200` widened, as the real `1e200*1e200` gives `9.999999999999999e+399`. Also right now: `sin(1000i)` is `0+9.850355570085235e+433i` (was `infj`), `exp(-1000+i)` is `2.742552296837872e-435+4.271272132365346e-435i` (was `0j`), `1/(1e-200i*1e-200i)` is `-1e+400+-0i` (was a Math error).
- A first version widened on any `inf` part, and `sinh(1000+i)*2` became `nannani` (was `inf+infi`): Sinh has no BigCx arm, so its `inf+infi` reached Mul, and Boost's BigComplex multiply turns `inf*0` into `nan` where `std::complex<double>` keeps the `inf`. An `inf` or subnormal part counts as an escape only when every Complex operand is finite (`complex_operands_finite`); the row `mul(inf+infi, 2) keeps an infinite operand's Complex` was red before that. The real `sinh(1000)*2` is `BigReal inf` on both builds.
- A subnormal imaginary literal stays a Complex, its constant spelling widens: `1e-310i` is `complex 1e-310j` (shown as `0`), `i1e-310` and `1e-310i*1` are `0+9.999999999999969e-311i`, the digits the subnormal double holds. The real arm does the same on f1777e0: `1e-310` is `float 1e-310`, `1e-310*1` is `BigReal 9.999999999999969e-311`.
