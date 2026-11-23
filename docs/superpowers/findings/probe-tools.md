# Probe tools

## 2026-11-23, chore/probe-tools cd23209: what native_probe does not show

`native_probe tokens` shunts the whole row. On an assignment the shunting_yard row is not the one evaluate walks: `tokens 'x=2+3'` gives `x  2  3  +  =`, while evaluate peels `x =` first (`value_tokens` in `eval.cpp`, an anonymous namespace) and shunts only `2 + 3`. Showing evaluate's row would need `value_tokens` in `eval.hpp`; a copy of the peel in the tool is not written. Left as it is.

`native_probe promote` shows apply's promotion steps (`promote_big`, `coerce`, `promote_complex`, `coerce`), not the real-first rewrite apply runs before them (`eval.cpp`, `TODO(#230)`): `promote root rat:-8/1 rat:1/3` shows `-8/1 1/3` unchanged through every step, while `apply root rat:-8/1 rat:1/3` is `Rational -512/1`, the degree `1/3` having become a power. Its help says so. Left as it is.
