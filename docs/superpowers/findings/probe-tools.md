# Probe tools

## 2026-11-23, chore/probe-tools cd23209: what native_probe does not show

`native_probe tokens` shunts the whole row. On an assignment the shunting_yard row is not the one evaluate walks: `tokens 'x=2+3'` gives `x  2  3  +  =`, while evaluate peels `x =` first (`value_tokens` in `eval.cpp`, an anonymous namespace) and shunts only `2 + 3`. Showing evaluate's row would need `value_tokens` in `eval.hpp`; a copy of the peel in the tool is not written. Left as it is.

`native_probe promote` shows apply's promotion steps (`promote_big`, `coerce`, `promote_complex`, `coerce`), not the real-first rewrite apply runs before them (`eval.cpp`, `TODO(#230)`): `promote root rat:-8/1 rat:1/3` shows `-8/1 1/3` unchanged through every step, while `apply root rat:-8/1 rat:1/3` is `Rational -512/1`, the degree `1/3` having become a power. Its help says so. Left as it is.

## 2026-11-23, chore/probe-tools af55a7b: the op alone in `probe layers` skips the exact rule

`scripts/probe layers "sin(π)" --unit RAD` gives `binding Rational 0/1` and `apply float 1.2246467991473532e-16` (`sin dbl:0x1.921fb54442d18p+1`); `native_probe apply` on that operand gives the same float, and `native_probe eval "sin(π)" --unit RAD` gives `Rational 0/1`. The op-alone row reads the operands as values (`root_operands`), so the exact rule, which reads the token, never runs there. A binding exact, apply double split on such a case is the exact rule, not a bug.
