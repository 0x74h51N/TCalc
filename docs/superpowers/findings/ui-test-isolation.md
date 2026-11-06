# UI test isolation

## 2026-11-02, master a88c553: test_theme_switch.py fails alone

Run alone, 6 tests of `tests/py/e2e/ui/test_theme_switch.py` fail with `RuntimeError: Internal C++ object (PySide6.QtWidgets.QMenu) already deleted.` at `_view_menu`/`_theme_action`, which walk menus through `.menu()` and `.actions()` (the pattern `docs/rules/ai/tests.md` forbids). Inside `make py-test` the same tests pass. Same 6 on a detached checkout of a88c553 and on `refactor/typed-config`:

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest tests/py/e2e/ui/test_theme_switch.py -q
```

Failing: `test_theme_is_first_in_view_menu`, `test_theme_items`, `test_theme_added_while_running_shows_when_the_menu_opens`, `test_stored_choice_is_checked`, `test_choosing_light_requests_qt_scheme_and_persists`, `test_choosing_kitty_restyles_without_a_scheme_change`.

## 2026-11-04, refactor/theme-areas 1ddcc5f: the cause is the interpreter, not the file running alone

The same 6 fail alone under the system `python` (PySide6 6.10.2) and pass alone under `.venv/bin/python` (PySide6 6.12.0), the interpreter `make` and the hooks use. At 1ddcc5f: 6 failed, 22 passed against 28 passed; with the theme-areas work on top: 6 failed, 36 passed against 42 passed.

```bash
PYTHONPATH=src python -m pytest -q tests/py/e2e/ui/test_theme_switch.py
PYTHONPATH=src .venv/bin/python -m pytest -q tests/py/e2e/ui/test_theme_switch.py
```

## 2026-11-06, test/python-test-layers: gone with the menu tests

The menu tests of `test_theme_switch.py` are removed. The file now passes alone under the system `python` (PySide6 6.10.2) as well: 40 passed.

```bash
PYTHONPATH=src python -m pytest tests/py/e2e/ui/test_theme_switch.py -q
```
