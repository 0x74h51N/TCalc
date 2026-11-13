# Native build warnings

## 2026-11-13, chore/type-safety-rules: the flags and what they found

`-Wall -Wextra -Wconversion -Wsign-conversion -Wold-style-cast` on the three native targets gave 1648 warnings, 35 distinct places (`cmake -S src/native -B <dir> -G Ninja -DCMAKE_CXX_FLAGS="<flags>"`, then `grep warning: | sort -u`). 1377 of the 1648 were `ops.hpp` repeated per translation unit.

- `ops.hpp` `dispatch` compiled every `Value` arm of every kernel, so an Int64 operand reached a double overload through an implicit conversion (`Negate`, `Percent`, the `TCALC_CALL` macros). `dispatch` now takes the row's arm mask and compiles only those arms.
- That Int64 path was not dead: `apply`'s retry after an exact kernel throws (`sqrt` of `Rational(2)`) downcast a single integral operand to Int64 and relied on the conversion. With the mask the native test `unit eval` failed with `unsupported operand type for √`; the retry now converts every operand with `as_double`, and it passes.
- `-Wmissing-field-initializers`: GCC 15 warns when a designated initializer leaves out a member with no default member initializer, clang does not. The omitted members got `{}`.
- `-Wswitch` in `tests/internal/test_helpers.hpp`: `Subscript`, `Sum`, `Prod`, `Char` and `Const` printed as `<unknown>` in failure messages.

The `NOLINT(clang-analyzer-optin.core.EnumCastOutOfRange)` lines sat on `ostream << BigReal`; the bindings now call `number::str(digits)`. Output for 15 BigReal and BigComplex values was diffed before and after: identical.

## 2026-11-13, chore/type-safety-rules: Release adds `-Warray-bounds`

The same flags in a clean Release build (`cmake -S src/native -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release`) add warnings that Debug never shows, since `-Warray-bounds` reads the optimizer's view. `eval.cpp:703` keeps `Add`'s `int` precedence (4 at most in the table) in a `std::uint8_t`; `-Wconversion` warns about it in Release only, and it stays. The rest are all `-Warray-bounds`:

- 11 in `test_transcendental.cpp` and `test_trig.cpp`, at each `(c.*tc.fn)(...)` member pointer call: "array subscript `int (**)(...)[0]` is partly outside array bounds of `Calculator [1]`". That is the virtual branch of a member pointer call reading a vtable pointer from the 1-byte `Calculator`, which has no virtual function, so the branch never runs. Two standalone repros (an empty class, a member pointer table, a lambda through `std::function`, with and without `final`) at `-O2 -Wall` gave no warning.
- 12 at `boost/multiprecision/cpp_int/bitwise.hpp:598`, inside Boost's `reduce_n_half_pi` for `cpp_bin_float<50>`, inlined into `arithmetic.cpp`.

## 2026-11-13, chore/type-safety-rules: the switches with a `default`

17 native `switch`es have a `default` (`git grep -n "default:" -- src/native/lib src/native/python`). A Debug build with `-DCMAKE_CXX_FLAGS="-Wswitch-enum"` names the enum values each `default` takes. None hides a value: the 7 in `trig.cpp` list `DEG`, `RAD` and `GRAD` (no warning, so the `default` is never reached), `closed_forms.cpp:784` lists every value, 3 switch on a `char`, and 6 use `default` for the rest of the enum on purpose (`value.hpp:63` takes `Cx`, `BigCx`, `Coll`; `exact.cpp:30` and `parser.cpp:964` pick a few of the `OpId`s; `closed_forms.cpp:260`, `eval.cpp:1098` and `parser.cpp:907` a few `TokenKind`s).
