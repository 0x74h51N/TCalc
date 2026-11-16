# An imaginary literal and a complex result past the double range

Issue #239, milestone First release. Measurements: [imaginary-range.md](../findings/imaginary-range.md). An Int64 past $2^{53}$ losing its last digit next to a complex is a separate cause, #240, and is not part of this spec.

## The bugs

1. An imaginary literal is always a Complex, so a magnitude a double cannot hold is lost: `1e400i` is `infi`, `1e-400i` is `0`, `99999999999999999999i` is `1.0000000000000000e+20i`. What follows carries it: `1e400i-1e400i` is `nani`, `(1e400i)^{2}` is `inf+nani`, `1e400+1e400i` is `1e+400+infi`. The same number written with the constant `i` is right today: `i1e400` and `1e400*i` are `0+1e+400i`, `i1e-400` is `0+1e-400i`.
2. A result on the Cx arm that leaves the double range is never widened, with operands a double holds. Overflow: `1e200i*1e200i` is `-inf+0j`, `1e308i+1e308i` is `infj`, `(2i)^{2000}` is `inf-infj`, `e^{1000+i}` is `inf+infj`, `sin(1000i)` is `infj`, `(1e300+1e300i)*(1e300+1e300i)` is `nan+infj`. Underflow: `1e-200i*1e-200i` is `0`, `1e-160i*1e-160i` is the subnormal `-1e-320+0j`, and `1/(1e-200i*1e-200i)` is a Math error from that zero.

## How these values flow today

`i` is read in two places. After a number (`3i`, `1e400i`) the tokenizer makes one NumberToken, and `literal_value` (`eval/literal.cpp`) reads it: `parse_real` gives the part before `i` as an Int64, a Double or a BigReal, and all three are narrowed with `to_double` into `Complex(0, magnitude)`. Anywhere else (`i`, `1e400*i`, `i1e400`) `i` is a ConstToken whose value is `Complex(0, 1)`, and `apply` multiplies it with the number: `coerce` lifts a BigReal and a Complex together to BigComplex (its `BigCx` branch), and an Int64 or a Double with a Complex to Complex. For an Int64 or a Double the two readers give the same value; they differ only for a BigReal.

`apply` (`eval/eval.cpp`) ends with `promote_range`. It reads the result only when it is a `double`: `escaped_double_range` reports `inf`, a subnormal, or a zero from operands that are not zero (`any_operand_zero`, Int64 and Double operands), except for an op with `Trait::ExactZero` (Add, Sub, Mod), whose zero is the answer. Then, when the op has a BigReal arm, `redispatch_big` lifts every operand with `lift_to_big` and runs the kernel again; a widened zero keeps the double. A `Complex` result returns at once.

`promote_big` runs before the kernel and widens a power whose operands predict a result a double cannot carry (`power_needs_big`). It returns when an operand is complex. Its reason to exist is the power that lands in range but inexact, real `10^{308}`; an overflow to `inf` is already caught after the kernel.

Every op with a Cx arm has a BigCx arm, except Sinh, Cosh, Tanh, Asin, Acos, Atan, Asinh, Acosh, Atanh and Polar (`ops::arms_of`, listed with a probe against `libcalc_core.a`). Their real arm has no BigReal arm either: `sinh(1000)` is `inf` today.

## Approaches

For the literal:

- The literal gives the value the constant path gives (chosen): a BigReal magnitude is a BigComplex, an Int64 or a Double stays a Complex. Every spelling of the same number agrees, and nothing in `coerce` changes.
- Every magnitude past the double's exact integers goes to BigComplex in the literal: rejected, `9007199254740993i` and `9007199254740993*i` would then differ, which they do not today. That digit belongs to #240.

For the Cx result:

- Range promotion reads a Complex result too, after the kernel (chosen): one place, beside the double rule, and the BigCx kernels exist for the ops that need them.
- `promote_big` reads a complex base before the kernel: rejected, every observed failure overflows to `inf` and is caught after the kernel; the only case it adds, `(10i)^{308}` as the inexact double `1e+308`, shows as `1e+308`.

## The fix

### 1. The imaginary literal keeps a BigReal magnitude

In the imaginary branch of `literal_value`, a BigReal from `parse_real` gives a BigComplex with a zero real part and the magnitude as its imaginary part. BigReal (`cpp_dec_float`) and the BigComplex component (`cpp_bin_float`) are different types; the magnitude converts through `BigComplexComponent`, the conversion `detail::real_to_big_complex` (`value.hpp`) makes, so the value is the one `i1e400` gives. The Int64 and Double arms keep `Complex(0, to_double(...))` as today. The literal's prefix branch (`i3`) stays as it is; the tokenizer makes `i3` a ConstToken and a NumberToken, so the app does not reach it.

### 2. Range promotion reads a Complex result

`promote_range` also reads a `Complex` result. The result has escaped the double range when:

- a part is `inf` or subnormal, the same tests the double rule makes on one value, and every Complex operand is finite: an `inf` from an op with no BigCx arm (`sinh(1000+i)*2`) came in, it did not escape, and Boost's BigComplex multiply would turn it into `nan`; or
- the whole value is `0+0i`, the op has no `Trait::ExactZero`, and no operand is zero.

A `nan` part is not a test of its own: every `nan` seen from finite operands comes with an `inf` part (`nan+infj`).

When the result has escaped and the op has a BigCx arm, the kernel runs again on the operands lifted with the existing `lift_to_big_complex`. A widened zero keeps the Complex, as the double rule keeps its double. An op with no BigCx arm keeps its Complex result, as the double rule does for an op with no BigReal arm.

`any_operand_zero` does not read Complex operands, and it does not need to for this: `0i*5` is `0` with a zero operand, the widened run confirms the zero, and the Complex is kept. It costs one BigComplex run for that input and changes no value.

The Double path of `promote_range` and `escaped_double_range` keeps its behavior. How the two arms share the code is the builder's call, within [code.md](../../rules/ai/code.md#style): the arm is told apart once, by the result's arm, and nothing shared branches on it again.

### 3. Nothing else changes

`coerce`, `promote_big`, `promote_complex`, the narrowings and the formatter stay as they are.

## Not in this spec

- A part that falls to zero while the other part holds the magnitude: `(1+1e-200i)*1e-200` is `1e-200+0j`, BigComplex `1e-200+1e-400i`. The lost part is $10^{-200}$ of the other one.
- `(10i)^{308}` as the inexact double `1e+308+0j`.
- Sinh, Cosh, Tanh, the inverse trig and hyperbolic ops and Polar, which have no BigCx arm: `sinh(1000+i)` stays `inf+infi`, as `sinh(1000)` stays `inf`.
- An Int64 past $2^{53}$ next to a complex: #240.
- The `0+` the formatter writes before a BigComplex with a zero real part: #235.
- `e^{z}`, a Pow whose base `e` is read as a double (#241). Widened, `e^{1000+i}` would be `1.064433965627533e+434+1.657757680453371e+434i` (Pow of `BigComplex("2.718281828459045", "0")` and `BigComplex("1000", "1")`), wrong from the 13th digit; `exp(1000+i)` widens through Exp to `1.064433965627625e+434+1.657757680453514e+434i`, the exact value to 16 digits. The real arm has the same fault today: `e^{1000}` is `1.970071114016942e+434`, `exp(1000)` is `1.970071114017047e+434`.

## Tests

Each bug row is a test that fails before its fix and passes after it. The rows go into the existing tables; no new test structure.

Native, `src/native/tests/unit/test_eval.cpp`:

- `literal_arm_cases`, arm `BigCx`: `1e400i` (an imaginary exponent past double), `1e-400i` (an underflowing imaginary exponent), `99999999999999999999i` (an imaginary integer past int64). The existing imaginary rows of `literal_cases` stay green.
- `range_promotion_arm_cases`, arm `BigCx`: Mul of `Complex(0, 1e200)` twice (overflow), Add of `Complex(0, 1e308)` twice (overflow), Mul of `Complex(0, 1e-200)` twice (underflow to zero), Mul of `Complex(0, 1e-160)` twice (subnormal), Mul of `Complex(1e300, 1e300)` twice (`nan+infj`), Pow of `Complex(0, 2)` and `2000` (overflow in a power), Exp of `Complex(1000, 1)`.
- `range_promotion_value_cases`, the other side of the rule, green before and after: Mul of `Complex(0, 1)` twice keeps `Complex(-1, 0)`; Sub of `Complex(1, 1)` twice keeps `Complex(0, 0)` (ExactZero); Mul of `Complex(0, 0)` and `Complex(5, 0)` keeps `Complex(0, 0)`.

End to end, `tests/py/e2e/test_eval_e2e.py`, rows of `test_native_eval_golden` with type `BigComplex`, an untyped expression string in and the value read through `str(out)`. The `complex` branch compares with `pytest.approx` and is not used for these rows. Inputs: `1e400i`, `1e-400i`, `1e400i-1e400i`, `(1e400i)^{2}`, `1e400+1e400i`, `1e200i*1e200i`, `1e-200i*1e-200i`, `(2i)^{2000}`, `exp(1000+i)`. The expected values are the mathematical ones, $10^{400}i$, $10^{-400}i$, $0$, $-10^{800}$, $10^{400}+10^{400}i$, $-10^{-400}$, $2^{2000}$, $e^{1000}(\cos 1 + i \sin 1)$, written in the text `str` gives for them. The last row is `exp(...)`, not `e^{...}`, for the reason under Not in this spec. `1e200i*1e200i` widens the double `1e200`, which is $10^{200}$ less $3 \times 10^{183}$, so its value is `-9.999999999999999e+399+0i`, the same digits its real counterpart `1e200*1e200` gives today (`9.999999999999999e+399`).

`make native-test` and `PYTHONPATH=src python -m pytest tests/py/e2e/test_eval_e2e.py` run the tests of what changes.
