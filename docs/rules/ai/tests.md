# Tests

## Layers

- Python evaluation logic is tested in `tests/py/unit/core/` against the fake `calc_native` from the conftest. Do not depend on the real native module there.
- End to end behavior (a real string through tokenize and evaluation, cross-line references, implicit multiplication, real collections) is tested in `tests/py/e2e/` with the real `calc_native`.
- Native behavior (tokenize, shunting yard, normalize) is tested in C++ under `src/native/tests/` (`make native-test`).

## Cases

- Add a case as a `param(...)` to the existing parametrized test, not as a new test function or a new file. End to end evaluation cases go into the golden parametrized test in `tests/py/e2e/test_eval_e2e.py`. Only a case that needs a genuinely different setup (for example stateful cross-line evaluation) gets its own function.
- Each param says what it is through its `id=`, short and descriptive, with no comment per case. Document the structure of the param tuple once, at the head of the table.
- Constants are tested end to end in Python, with the exact type and the exact value: no `float()` conversion and no tolerance. A unit test that checks a constant's value against a fake is meaningless.
- Native tokenize correctness is a row in the data-driven `tok_cases` table; implicit multiplication and RPN order are a row in `shunt_cases`. Do not write a one-off case that re-implements tokenize and compare.
- Native test cases are a typed struct with designated initializers in one vector. Calls with the same signature share one table and one loop; the function to call is a field of the row (a member function pointer, cast to pin an overload), and the function is told apart in the `id` (`"exp :: ln two"`). Field names say input and expected (`input`, `expected`, `tol`; `x`, `y` for binary). `tol == 0` means exact equality. BigReal inputs and expected values are text, so no double sneaks in. Overloads with a different signature, `EXPECT_THROWS` rows and ordering claims stay as single test cases with a one-line reason.
- Native tests use `test_detail::with_case(ctx, id, ...)`, not raw `TEST` macros or `EXPECT_NE`.

## What earns a test

- Test behavior, not the final state. A pure relocation or rename, or a UI element with no behavior yet, gets no new "assert the final shape" test; the existing suite staying green is the verification. Real behavior (a dock toggle kept in sync with its menu check and the app state) does deserve an integration test.
- A test that restates the implementation is not written.
- A test that counts is not a test that reads. A green suite is not the last check: run the app and look at the change.
- A red check is fixed or pinned, never silenced. A pin carries its reason and date beside the value it pins, and a numeric pin records today's value so the number can only improve. Editing the expected number until the check passes is how a check dies.

## UI tests and running

- In UI tests, do not walk menus through `.menu()` or `.actions()`; untracked `QMenu` wrappers get garbage collected. Use the references the controller keeps. Isolate `QSettings` in a temporary INI file and reset the app state singleton. Check visibility with `isHidden()`, since `isVisible()` is unreliable offscreen.
- Run the Python suite with `make py-test`, never as one pytest process over `tests/py`: one process leaks Qt state between the suites and gives false failures. To run a single UI test file in isolation, use `PYTHONPATH=src python -m pytest <file>`.
