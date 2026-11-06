# Python test layers, part 2: the theme tests in `tests/py/ui` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The theme tests in `tests/py/ui` and `tests/py/e2e/ui` read no bundled theme and have typed rows, and the folder lives at `tests/py/e2e/ui`.

**Architecture:** The test themes and fixtures go first, then the files in scope, and the move is the last step.

**Tech Stack:** pytest, pytest-qt, PySide6.

**Spec:** [2026-11-06-ui-theme-tests-design.md](../specs/2026-11-06-ui-theme-tests-design.md)

## Global Constraints

- No file under `src/` changes, and no package is added.
- Only the scope in the spec changes: `test_expression.py` and the other tests are not touched.
- Rows follow `docs/rules/ai/tests.md`, section "Cases".
- Run with `PYTHONPATH=src .venv/bin/python -m pytest <file> -q`. The whole suite runs as `make py-test PYTEST_ARGS=-q`.
- A commit needs the owner's approval: each commit step shows the diff and stops. Run `make py-lint-fix` first.

## Review Focus

- A pixel test that passes because a test color equals the widget's default: the 32 values in each test theme differ from each other.
- A test theme that falls behind the bundled color names: `test_test_themes_name_the_bundled_colors` fails.
- A test outside the scope that relied on bundled colors once the fixtures turn autouse: task 1 runs the whole folder and reports it before anything else changes.

## Task 1: Test themes, fixtures and the files part 1 moved

**Files:**
- Create: `tests/py/ui/themes/dark.toml`, `tests/py/ui/themes/light.toml`, `tests/py/conftest.py`
- Modify: `tests/py/ui/conftest.py`, `tests/py/e2e/ui/conftest.py`, `tests/py/e2e/ui/test_theme_on_widgets.py`, `tests/py/e2e/ui/test_icons_on_themes.py`

**Builds on:** the `extreme` theme, `_user_themes` and `write_theme` in the two conftests.

**Interfaces:**
- Produces: `_user_themes`, `own_themes` and `theme_table(table: dict[str, object], base: str = "dark") -> str` in `tests/py/conftest.py`, none autouse. An autouse fixture in `tests/py/ui/conftest.py` and in `tests/py/e2e/ui/conftest.py` requests `_user_themes` and `own_themes`.

- [ ] **Step 1: Write the two themes as the spec says**

The color names are the 32 of `src/tcalc/themes/dark.toml`.

- [ ] **Step 2: Write the fixtures**

`own_themes` is `monkeypatch.setattr("tcalc.theme.BUILT_IN_DIR", Path(__file__).parent / "ui" / "themes")`. `theme_table` imports `tcalc.theme` in its body, so `tests/py/unit` loads nothing through this conftest. `extreme_theme`, `write_theme` and the `TODO(test themes)` go.

- [ ] **Step 3: Run both folders, before fixing anything**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/ui -q` and `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/ui -q`
Expected, as the probe in the finding measured: in `tests/py/ui` 10 failures (`test_toolbar_spin_boxes...` 3, `test_a_saved_primary_key...` 3, `test_raised_edge_shadow...[dark]`, `test_switch_reaches_open_widgets`, `test_theme_items`, `test_choosing_kitty...`), and in `tests/py/e2e/ui` 4 (`test_kitty_uses_its_base_variant_files`, `test_every_qss_placeholder_resolves` 3). A failure anywhere else is outside the scope: stop and report it to the owner.

- [ ] **Step 4: Fix the two moved files as the spec's "The other theme tests" says**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/ui -q`
Expected: all pass, with `test_every_qss_placeholder_resolves` at 3 cases.

- [ ] **Step 5: No commit yet**

`tests/py/ui` is red until task 3. The commit is at the end of task 3.

## Task 2: `test_theme_switch.py`

**Files:**
- Modify: `tests/py/ui/test_theme_switch.py`

**Builds on:** the file as it is, test by test in the spec.

- [ ] **Step 1: Split `state` out of `window`, remove the 4 menu tests, `_view_menu` and `_theme_action`**

`state` does the `QSettings` patches, resets `_app_state`, keeps the palette and sheet, and calls `load_theme("dark")`; afterwards it loads dark and restores them. `window` requests it and does the rest.

- [ ] **Step 2: Write the 2 tests that call the function, and remove the 5 the spec names**

`ViewOperations` comes from `tcalc.ui.controller.menubar.view`. `QStyleHints.setColorScheme` is patched as it is today.

- [ ] **Step 3: Toml strings to dicts, lambdas to named functions**

Each `(_user_themes / x / "theme.toml").write_text(...)` plus `apply_theme(qapp, x)` becomes `apply_theme(qapp, theme_table({...}))`. `round_theme` and `edged_theme` return `theme_table(...)`, and stay before `window` in the test signature, so the table is there when `window` applies `{"theme": "user"}`. `extreme_theme` becomes `"extreme"`. `test_switch_reaches_open_widgets` compares `Display` with `LIGHT_SCREEN = QColor("#FEFEFE")`.

```python
@dataclass(frozen=True, slots=True)
class FontRangeCase:
    table: dict[str, object]
    widgets: Callable[[MainWindow], list[QWidget]]
    top: str  # the range's top in DEFAULT_LOOK, read with attrgetter
```

- [ ] **Step 4: Prove it bites**

On a scratch copy of `src/`: remove `app.setStyleSheet(...)` in `apply_theme`, and expect the chain tests to fail; remove `app.setPalette(...)`, and expect `test_light_scheme_sets_light_palette` to fail, since a widget's background comes from the stylesheet; remove the `sync_theme` call in `set_theme`, and expect `test_set_theme_custom_restyles_without_a_scheme_change` to fail. In `_populate_custom_themes`, stop rebuilding the actions, remove `setChecked` and remove the `triggered` connection, and expect its 3 new tests to fail one by one.

- [ ] **Step 5: Run alone, with both interpreters**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/ui/test_theme_switch.py -q` and the same under the system `python`.
Expected: all pass under the venv. Under the system `python`, none of the 6 failures recorded in `ui-test-isolation.md`, which were the menu tests, so that finding is updated.

## Task 3: The theme tests of `test_history.py` and `test_custom_pad_layout.py`

**Files:**
- Modify: `tests/py/ui/test_history.py:279-472`, `tests/py/ui/test_custom_pad_layout.py:180-197`

**Builds on:** `apply_user_theme`, `themed` and `_key_color` as they are.

- [ ] **Step 1: `test_history.py`, as the spec says**

```python
@dataclass(frozen=True, slots=True)
class HistoryThemeCase:
    table: dict[str, object]
    shown: Callable[[History], object]
    expected: str | int | bool  # a str names a color of the theme
```

`"#123456"` and `"#FFEE00"` are the test's own values and stay.

- [ ] **Step 2: `test_custom_pad_layout.py`, as the spec says**

- [ ] **Step 3: Prove the spin box test bites**

On a scratch copy of `src/`: make `KSSpinBox` take the app font. Expected: `test_toolbar_spin_boxes_keep_their_font_and_fit_under_a_big_app_font` fails. Rename a color in the bundled `dark.toml`: `test_test_themes_name_the_bundled_colors` fails.

- [ ] **Step 4: Run the folder**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/ui -q`
Expected: all pass, 12 xfailed and 4 xpassed as before, and the count differs from the old one only by what the spec's Done when lists. `grep -rnE '"(kitty|retro|sponge)"' tests/py` finds nothing.

- [ ] **Step 5: Show the diff of tasks 1 to 3, commit on approval**

`test/theme: the theme tests run on test themes, with typed rows`

## Task 4: `tests/py/e2e/test_bundled_themes.py`

**Files:**
- Create: `tests/py/e2e/test_bundled_themes.py`. New because the tests of `tests/py/e2e/ui` run on the test themes and no other file checks the bundled ones as a whole; `test_theme_readability.py` checks only contrast.
- Modify: `tests/py/e2e/ui/test_theme_on_widgets.py`, which gives it `test_test_themes_name_the_bundled_colors`

**Builds on:** `Theme`, which raises or logs what it skips, and `_build_stylesheet`.

- [ ] **Step 1: Write the tests the spec names**

- [ ] **Step 2: Prove they bite**

On a scratch copy of `src/`: an alpha color, broken toml, an unknown key, a look naming a missing color, an extra color name, a dropped and a renamed color, a wrong picture file, an unknown QSS placeholder and an unknown key in the template each fail a test. A valid new color fails none.

## Task 5: The move to `tests/py/e2e/ui`

**Files:**
- Move: `git mv` each of `tests/py/ui/test_*.py`, and `tests/py/ui/themes`, into `tests/py/e2e/ui/`
- Modify: `tests/py/e2e/ui/conftest.py`, `makefile:32-40`, `docs/rules/ai/tests.md`
- Delete, once merged: `tests/py/ui/conftest.py`, `tests/py/conftest.py`

**Builds on:** the folder and the `makefile` lines part 1 made.

- [ ] **Step 1: Count before**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/ui --collect-only -q | tail -1` and the same for `tests/py/e2e/ui`. Note both.

- [ ] **Step 2: Move and merge**

`tests/py/e2e/ui/conftest.py` takes `qapp`, `expression_widget` and `set_expression` from `tests/py/ui/conftest.py`, and `_user_themes`, `own_themes` and `theme_table` from `tests/py/conftest.py`. The `BUILT_IN_DIR` path becomes `Path(__file__).parent / "themes"`. The `makefile` loses `pytest tests/py/ui`, and `py-test-ui` runs `tests/py/e2e/ui`.

- [ ] **Step 3: Grep the whole tree for the old path**

Run: `grep -rnE 'tests/py/ui|tests\.py\.ui' . --exclude-dir=build --exclude-dir=.venv --exclude-dir=.git`
Expected: only dated findings and specs. Update the rest, and name `tests/py/e2e/ui` in the layers section of `docs/rules/ai/tests.md`.

- [ ] **Step 4: Run everything**

Run: `make py-test PYTEST_ARGS=-q py-lint typecheck`
Expected: pass, and `tests/py/e2e/ui` collects the sum of the two counts of step 1.

- [ ] **Step 5: Show the diff, commit on approval**

`test: tests/py/ui is the e2e of the UI, move it to tests/py/e2e/ui`
