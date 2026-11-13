# Native build warnings

## 2026-11-13, chore/type-safety-rules: the flags and what they found

`-Wall -Wextra -Wconversion -Wsign-conversion -Wold-style-cast` on the three native targets gave 1648 warnings, 35 distinct places (`cmake -S src/native -B <dir> -G Ninja -DCMAKE_CXX_FLAGS="<flags>"`, then `grep warning: | sort -u`). 1377 of the 1648 were `ops.hpp` repeated per translation unit.

- `ops.hpp` `dispatch` compiled every `Value` arm of every kernel, so an Int64 operand reached a double overload through an implicit conversion (`Negate`, `Percent`, the `TCALC_CALL` macros). `dispatch` now takes the row's arm mask and compiles only those arms.
- That Int64 path was not dead: `apply`'s retry after an exact kernel throws (`sqrt` of `Rational(2)`) downcast a single integral operand to Int64 and relied on the conversion. With the mask the native test `unit eval` failed with `unsupported operand type for √`; the retry now converts every operand with `as_double`, and it passes.
- `-Wmissing-field-initializers`: GCC 15 warns when a designated initializer leaves out a member with no default member initializer, clang does not. The omitted members got `{}`.
- `-Wswitch` in `tests/internal/test_helpers.hpp`: `Subscript`, `Sum`, `Prod`, `Char` and `Const` printed as `<unknown>` in failure messages.

The `NOLINT(clang-analyzer-optin.core.EnumCastOutOfRange)` lines sat on `ostream << BigReal`; the bindings now call `number::str(digits)`. Output for 15 BigReal and BigComplex values was diffed before and after: identical.
