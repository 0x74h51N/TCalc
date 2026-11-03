# UI test isolation

## 2026-11-02, master a88c553: test_theme_switch.py fails alone

Run alone, 6 tests of `tests/py/ui/test_theme_switch.py` fail with `RuntimeError: Internal C++ object (PySide6.QtWidgets.QMenu) already deleted.` at `_view_menu`/`_theme_action`, which walk menus through `.menu()` and `.actions()` (the pattern `docs/rules/ai/tests.md` forbids). Inside `make py-test` the same tests pass. Same 6 on a detached checkout of a88c553 and on `refactor/typed-config`:

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest tests/py/ui/test_theme_switch.py -q
```

Failing: `test_theme_is_first_in_view_menu`, `test_theme_items`, `test_theme_added_while_running_shows_when_the_menu_opens`, `test_stored_choice_is_checked`, `test_choosing_light_requests_qt_scheme_and_persists`, `test_choosing_kitty_restyles_without_a_scheme_change`.
