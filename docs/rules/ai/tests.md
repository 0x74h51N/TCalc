# Tests

## Layers

- Python evaluation logic is tested in `tests/py/unit/core/` against the fake `calc_native` from the conftest. Do not depend on the real native module there.
- End to end behavior (a real string through tokenize and evaluation, cross-line references, implicit multiplication, real collections) is tested in `tests/py/e2e/` with the real `calc_native`.
- The e2e of the UI (a real widget or window, and the chain from a theme to what it paints) is in `tests/py/e2e/ui/`. It runs on the test themes in `tests/py/e2e/ui/themes/`, and no test there reads a bundled theme.
- The bundled themes are checked in `tests/py/e2e/test_bundled_themes.py`: broken toml, a key or color with no counterpart, a missing picture, an unresolved QSS placeholder. A changed color value breaks nothing there.
- Native behavior (tokenize, shunting yard, normalize) is tested in C++ under `src/native/tests/` (`make native-test`).

## What a unit test is

- A unit test tests one small function. It is the simplest use of that function, and it checks that the function works.
- While testing it, the test does not import or use another function, type or dependency. It imports only the function under test, by name: no module alias, no other production function, no production type or value. In a file that tests more than one function, the import sits inside the test, under its `def`, and a helper or fixture that needs one does the same; a file that tests one function keeps its one import at the top. `tests/py/unit/ruff.toml` keeps it to one name per line.
- Where the function branches on a type or calls another function, the test writes its own fake type or dummy and patches that name by its dotted path: `monkeypatch.setattr("tcalc.ui.look.ColorName", FakeColor)`. `tests/py/unit/core` is the shape to copy.
- Read the function and understand what it does before writing its test. A test is not discovered by trying things in a scratch file.
- Each function gets one normal use, plus its own error if rejecting something is its job. Where dispatching is the job, each arm gets one row.
- The important functions all have their test: what reads a file, what converts it, what catches its errors, what applies the result, each one alone.
- A test that goes through a chain of functions is an e2e test. It lives under `tests/py/e2e/`, never in the unit layer, however small it looks.
- A menu button is not tested. User interaction test goes to e2e test. The function behind it is, called directly for unit test.
- A unit test reads no bundled theme, and no real theme name appears in one. The one named exception is `tests/py/unit/ui/test_theme_readability.py`. The strings `light` and `dark` appear only where the function under test hard-codes them (`ThemeChoice.variant`, `Theme.scheme`).

## Cases

- Add a case as a `param(...)` to the existing parametrized test, not as a new test function or a new file. End to end evaluation cases go into the golden parametrized test in `tests/py/e2e/test_eval_e2e.py`. Only a case that needs a genuinely different setup (for example stateful cross-line evaluation) gets its own function.
- Each param says what it is through its `id=`, short and descriptive, with no comment per case. Document the structure of the param tuple once, at the head of the table.
- A row of one or two plain values is a `param`; a row with more fields is a frozen dataclass. Rows hold no toml strings and no lambdas. A lambda handed to `monkeypatch.setattr` is not a row and stays.
- Constants are tested end to end in Python, with the exact type and the exact value: no `float()` conversion and no tolerance. A unit test that checks a constant's value against a fake is meaningless.
- Native tokenize correctness is a row in the data-driven `tok_cases` table; implicit multiplication and RPN order are a row in `shunt_cases`. Do not write a one-off case that re-implements tokenize and compare.
- Native test cases are a typed struct with designated initializers in one vector. Calls with the same signature share one table and one loop; the function to call is a field of the row (a member function pointer, cast to pin an overload), and the function is told apart in the `id` (`"exp :: ln two"`). Field names say input and expected (`input`, `expected`, `tol`; `x`, `y` for binary). `tol == 0` means exact equality. BigReal inputs and expected values are text, so no double sneaks in. Overloads with a different signature, `EXPECT_THROWS` rows and ordering claims stay as single test cases with a one-line reason.
- Native tests use `test_detail::with_case(ctx, id, ...)`, not raw `TEST` macros or `EXPECT_NE`.

## Operation results, precision and errors

- A test or a finding about the result of an operation, a precision loss or the catching of an error is first an e2e test with the binding in it: the expression through `tokenize`, `evaluate_branch` and `format_result`, as `tests/py/e2e/test_eval_e2e.py` does.
- The layers are first looked at with the probe tools ([probe.md](../../probe.md)): `scripts/probe eval` and `layers`, then `scripts/native_probe apply`, `promote` and `kernel`, with the table pasted as evidence.
- To find where the problem comes from, the same case then runs on the other layers on its own: `calc_native.apply` with its `OpId` (the op alone), `format_result` (the text), and the native e2e without the binding (`src/native/tests/`). The first layer that goes wrong is the source.
- The case is written in the flat op form (`(1)⌄(2)`, `(2)⁻¹`), apart from the LaTeX pipeline (`MathNode`, `structural_split`). A test or a finding names the op, not the LaTeX form.
- Each op a form reaches is tried on its own. Read the op id from the tokens before assuming two forms share one: `\root{a}{b}` and `⌄` are both `OpId.Root`, `^{}` is `OpId.Pow`, `⁻¹` is `OpId.Recip`.
- Only a form the editor or the keypad produces is tested. A name in an op's aliases is not a form to type: `2 pow 3` is not an expression, and its result is no finding.
- When the LaTeX form is tested too and does not give the result the flat form gives, look at the op the LaTeX form maps to and at the split, not at the op.
- A chain of operations is not tested in LaTeX form. `2^{3}^{4}` gives `4096`: the tokenizer runs `2^3` first and then `8^4`, while the GUI does not show it that way. The correct writing is `(2^{3})^{4}`, or `2^{3^{4}}` for a power on the exponent; that is a LaTeX writing rule and belongs to render. A chain is tested without LaTeX, so a writing mistake never stands for a wrong chain result.

## What earns a test

- Test behavior, not the final state. A pure relocation or rename, or a UI element with no behavior yet, gets no new "assert the final shape" test; the existing suite staying green is the verification. Real behavior (a dock toggle kept in sync with its menu check and the app state) does deserve an integration test.
- A test that restates the implementation is not written.
- A test that counts is not a test that reads. A green suite is not the last check: run the app and look at the change.
- A red check is fixed or pinned, never silenced. A pin carries its reason and date beside the value it pins, and a numeric pin records today's value so the number can only improve. Editing the expected number until the check passes is how a check dies.

## UI tests and running

- In UI tests, do not walk menus through `.menu()` or `.actions()`; untracked `QMenu` wrappers get garbage collected. Use the references the controller keeps. Isolate `QSettings` in a temporary INI file and reset the app state singleton. Check visibility with `isHidden()`, since `isVisible()` is unreliable offscreen.
- An assistant runs only the tests of what it changed: the unit tests of the function it touched, or the test file or directory of the code it changed (`PYTHONPATH=src python -m pytest <file>`). It does not run the whole Python suite (`make py-test`) unless it is really needed, for example a change that every area reads (the ops table, the theme loader) or the human agent asking for it. The whole suite takes minutes and stalls the work; the pre-push hook runs it, by the rules CI uses.
- Never run the suite as one pytest process over `tests/py`: one process leaks Qt state between the suites and gives false failures.
