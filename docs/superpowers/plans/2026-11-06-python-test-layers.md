# Python test layers, part 1: `tests/py/unit/ui` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every test in `tests/py/unit/ui` calls one small function alone, in its simplest use, and what runs a chain moves to `tests/py/e2e/ui` or is deleted.

**Architecture:** First the folder is cleared. Then one task per module writes its small tests.

**Tech Stack:** pytest, pytest-qt, PySide6.

**Spec:** [2026-11-06-python-test-layers-design.md](../specs/2026-11-06-python-test-layers-design.md)

## Global Constraints

- Nothing under `src/` changes. No fake `calc_native` is written.
- Before a function's test is written, the function is read, and what it does is said in one sentence in the task report.
- Every test follows `docs/rules/ai/tests.md`, sections "What a unit test is" and "Cases". The one exception is `test_theme_readability.py`, which reads the bundled themes.
- A file that breaks a rule is not committed to be fixed by a later task. The tasks are the order of the work; what reaches a commit already follows the rule.
- `tests/py/ui/test_expression.py`, the existing files of `tests/py/e2e/` and `tests/py/unit/core/` are not touched, except the import lines `tests/py/unit/ruff.toml` changes in `unit/core/conftest.py` and `unit/core/test_ops.py`. No package is added.
- Run a file with `PYTHONPATH=src .venv/bin/python -m pytest <file> -q`, using the venv: the system `python` has an older PySide6 and gives false failures. The whole suite runs as `make py-test PYTEST_ARGS=-q`.
- The moves in this plan are named, so they are done with `git mv`. Nothing else is moved or deleted.
- A commit needs the human agent's approval: each commit step shows the diff and stops. Run `make py-lint-fix` first.
- No em dash. Comments say why. No `type: ignore` in a test: tests are not in mypy. A new test file starts with the SPDX header its neighbours have and `from __future__ import annotations`.

## Review Focus

- A chain test passing as a unit test: read each test and name the one function it calls.
- A row whose expected value restates the code: each task breaks the function on a scratch copy of `src/` and sees its test fail by name.
- A test depending on a machine's user folder: `user_themes_dir` is patched wherever a function reads it.
- State leaking through the global theme: `_theme_instance` is patched by `monkeypatch`, and the directory runs in reverse order at the end.

## Task 1: Clear the folder

**Files:**
- Create: `tests/py/e2e/ui/conftest.py`, `tests/py/e2e/test_working_directory.py`, `tests/py/helpers.py`
- Move: `git mv tests/py/unit/ui/test_styles.py tests/py/e2e/ui/test_theme_on_widgets.py`
- Move: `git mv tests/py/unit/ui/test_format_result.py tests/py/e2e/ui/test_format_result_e2e.py`
- Move: `git mv tests/py/unit/ui/test_icons.py tests/py/e2e/ui/test_icons_on_themes.py`
- Move: `tests/py/unit/theme/test_look.py` and `test_theme.py` into `tests/py/unit/ui`, replacing the old `test_look.py`, and remove the empty `tests/py/unit/theme`
- Modify: `makefile`, `tests/py/unit/ui/conftest.py`, `test_color_scheme.py`, `test_theme_colors.py`, `test_theme_overrides.py`, `test_typed_tables.py`, `test_picture_layer.py`, `tests/py/ui/test_history.py:26`, `docs/rules/ai/tests.md` (already edited, goes in this commit)
- Delete, once empty: `tests/py/unit/ui/test_theme_overrides.py`

**Builds on:** the `_user_themes` and `write_theme` fixtures of `tests/py/unit/ui/conftest.py`, the two test files already in `tests/py/unit/theme/`, `_opaque_color` in `test_icons.py`.

**Interfaces:**
- Produces: `tests.py.helpers.opaque_color(icon: QIcon) -> QColor`, the former `_opaque_color`, imported as `from tests.py.helpers import opaque_color`.

- [ ] **Step 1: Make `tests/py/e2e/ui/`, with a conftest holding `_user_themes` and `write_theme`**

`write_theme` leaves `tests/py/unit/ui/conftest.py`: all its users move or are deleted here. The environment lines come from `tests/py/e2e/conftest.py`. The `makefile` target: `pytest tests/py/e2e --ignore=tests/py/e2e/ui`, then `pytest tests/py/e2e/ui`, and the `tests/py/unit/theme` line goes.

- [ ] **Step 2: Move what the spec's "What moves" names, with the helpers it names**

`_opaque_color` becomes `opaque_color` in `tests/py/helpers.py`, and `tests/py/ui/test_history.py:26` imports it from there.

- [ ] **Step 3: Delete what the spec's two "Deleted" sections name, reading each body once**

`test_only_keypad_qss_uses_keypad_colors` goes into `test_props.py`, and `git mv tests/py/unit/ui/test_props.py tests/py/e2e/ui/test_props.py` moves it.

New: `tests/py/unit/ruff.toml` with `force-single-line`, so ruff enforces one imported name per line in unit tests and nowhere else. In a file that tests more than one function, each test imports its function inside its body, under the `def`; a helper or fixture that needs one does the same. A file that tests one function keeps its one import at the top.

`FORMAT_CASES` in `test_format_result_e2e.py` becomes frozen `FormatCase` rows. `test_every_qss_placeholder_resolves` and `test_theme_readability.py` derive their theme list from the `themes` folder.

- [ ] **Step 4: Run**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/ui -q` and `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e/ui -q` and `PYTHONPATH=src .venv/bin/python -m pytest tests/py/e2e --ignore=tests/py/e2e/ui -q` and `PYTHONPATH=src .venv/bin/python -m pytest tests/py/ui/test_history.py -q`
Expected: all pass. `e2e` is 408: the 407 of before and `test_working_directory.py`.

- [ ] **Step 5: Grep for the old paths, show the diff, commit on approval**

Run: `grep -rnE 'unit/(theme|ui/test_(format_result|styles|theme_overrides|icons))|unit\.ui\.test_icons' tests docs/rules makefile`
`test/ui: the unit test rule, chain tests move to e2e/ui or go`

## Task 2: `test_typed_tables.py`

**Files:**
- Modify: `tests/py/unit/ui/test_typed_tables.py`

**Builds on:** its `Fit`, `Inner`, `Outer`, `GOOD`, `BUILT`.

- [ ] **Step 1: Read `tcalc/typed_tables.py`, then write one small test per function from the spec's list**

The hints are the test's own: `FakeNew = NewType(...)`, `Fit`, `Inner`. `_convert` takes a frozen row:

```python
@dataclass(frozen=True, slots=True)
class ConvertCase:
    value: object
    hint: object
    expected: object
```

The existing `test_build` and `test_override` rows shrink to the spec's cases.

- [ ] **Step 2: Prove it bites**

On a scratch copy of `src/`: remove the `isinstance(table, dict)` check in `_convert_keys`; change `type(value) is hint` to `isinstance`; remove the `value in enum.__members__` branch. Each must fail its own test by name.

- [ ] **Step 3: Run alone, show the diff, commit on approval**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/ui/test_typed_tables.py -q`
`test/typed_tables: each function alone`

## Task 3: `test_look.py`

**Files:**
- Modify: `tests/py/unit/ui/test_look.py`

**Builds on:** the working shape at the scratchpad's `owntypes/test_own_types.py`.

- [ ] **Step 1: Read `tcalc/ui/look.py`, then rewrite the file to the spec's list**

The import is `from tcalc.ui.look import Tinted, _hover_follows_color, _merged, look_fields, qss_name, with_shared_buttons`. A fixture patches `tcalc.ui.look.ColorName`, `ColorRef` and `Tinted` with the test's `FakeColor`, `FakeRef = FakeColor | FakeTinted` and `FakeTinted`. `qss_name` takes `SimpleNamespace(path=("a", "b"))`. `look_fields` results compare as plain tuples through `astuple`. `with_shared_buttons` gets dummy classes over `KeypadLook`, `HistoryLook` and `Button`, and asserts on dicts.

- [ ] **Step 2: Prove it bites**

On a scratch copy of `src/`: remove `or "opacity" in base`; remove `"hover_color" not in key`; remove each color branch of `look_fields`. Each must fail its own test.

- [ ] **Step 3: Run alone, show the diff, commit on approval**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/ui/test_look.py -q`
`test/look: each function alone`

## Task 4: `test_theme.py`

**Files:**
- Modify: `tests/py/unit/ui/test_theme.py`, `tests/py/unit/ui/test_color_scheme.py` (its `ThemeChoice` rows come out; its four `AppState` tests stay until task 8)

**Builds on:** the `custom_theme_folders`, `get_theme` and `load_theme` tests already in the file, and the `ThemeChoice` rows of `test_color_scheme.py`.

- [ ] **Step 1: Read `tcalc/theme.py`, then add one small test per function from the spec's list**

The import is by name (`from tcalc.theme import Theme, ThemeChoice, ThemeMode, ThemeError, _opaque, ...`), replacing the `theme_mod` alias. Methods run on a bare instance:

```python
def _theme(colors):
    theme = Theme.__new__(Theme)
    theme.variant, theme.colors = "x", colors
    return theme
```

`_known_colors` gets `look_fields` patched to return the test's fake fields, `ColorField` to that fake's class, `_restored` to a recorder, `DEFAULT_LOOK` to a dummy. `_pictures` gets `build` patched to return a dummy dataclass or raise `TableError`, and `_folder` to a fixed path. `Theme.__init__` gets `_read`, `override`, `with_shared_buttons`, `_known_colors`, `_pictures` patched. The `ThemeChoice` custom rows use a fake `Theme`.

- [ ] **Step 2: Prove it bites**

On a scratch copy of `src/`: remove the alpha check in `_opaque`; catch nothing in `_read`; remove the `_restored` call in `_known_colors`. Each must fail its own test.

- [ ] **Step 3: Run alone, show the diff, commit on approval**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/ui/test_theme.py -q`
`test/theme: each function alone`

## Task 5: `test_styles.py`

**Files:**
- Create: `tests/py/unit/ui/test_styles.py`

**Builds on:** `qss_color`, `apply_theme`, `sync_theme` as they are.

- [ ] **Step 1: Read them, then write the tests from the spec's list**

```python
def test_apply_theme(monkeypatch):
    monkeypatch.setattr("tcalc.ui.styles.load_theme", calls.append)
    monkeypatch.setattr("tcalc.ui.styles._build_palette", lambda: "palette")
    ...
    apply_theme(FakeApp(), "x")
    assert calls == ["x"] and app.palette == "palette" and app.sheet == "sheet"
```

`sync_theme` gets `get_app_state` patched to `SimpleNamespace(theme=SimpleNamespace(variant=lambda _s: "x"))`.

- [ ] **Step 2: Prove it bites**

On a scratch copy of `src/`: remove `app.setPalette(...)`; remove the `variant != get_theme().variant` check. Each must fail its own test.

- [ ] **Step 3: Run alone, show the diff, commit on approval**

`test/styles: apply_theme, sync_theme and qss_color alone`

## Task 6: `test_ui_utils.py`

**Files:**
- Create: `tests/py/unit/ui/test_ui_utils.py`

**Builds on:** `_apply_tint`, `_load_icon`, `get_icon`, `theme_icon` as they are. The pixel read is the test's own; a unit test does not import `opaque_color`.

- [ ] **Step 1: Read `tcalc/ui/utils.py`, then write `split_camel`, `_apply_tint`, `_load_icon`, `get_icon`, `theme_icon` from the spec's list**

`_apply_tint` takes a `QIcon` of a filled `QPixmap`. `_load_icon` gets `ICONS_DIR` patched to `tmp_path`, `CONFIG` and `get_theme` to dummies. `theme_icon` takes a `build` returning such an icon.

- [ ] **Step 2: Prove it bites**

On a scratch copy of `src/`: make `_apply_tint` return its icon untinted; make `_load_icon` skip the family file. Each must fail its own test.

- [ ] **Step 3: Run alone, show the diff, commit on approval**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/ui/test_ui_utils.py -q`
`test/icons: each function alone`

## Task 7: Widgets, one module per file

**Files:**
- Create: `tests/py/unit/ui/test_button.py`, `test_toaster.py`, `test_common_utils.py`, `test_widget_utils.py`
- Delete, once empty: `tests/py/unit/ui/test_common_widgets.py`
- Modify: `tests/py/unit/ui/test_picture_layer.py`

**Builds on:** the classes of `test_common_widgets.py`, which get a dummy `get_theme`, and `SimpleNamespace(pictures=...)` as `test_empty_box_is_not_rendered` patches `get_theme`.

- [ ] **Step 1: Split `test_common_widgets.py` as the spec says, and add `fit_radius`, `shortest_side`, `set_raised` to `test_widget_utils.py`**

- [ ] **Step 2: In `test_picture_layer.py`, do what the spec says**

The `sponge` fixture, `_window_picture`, `sponge_window_layer` and `load_theme("kitty")` give way to a dummy `get_theme` whose `pictures` hold a dummy picture on an svg in `tmp_path`, 600 by 300. `picture_rects`' `ThemePicture` becomes a dummy too. `_natural_size` and `_render` get a test of their own and are patched everywhere else. `test_button_count`, `test_size_policy_fixed`, `test_alignment_center` and `test_word_wrap_off` are deleted: they only read back a constructor setting. The `OptionGroup` fixture sends `DeferredDelete` in teardown, so its fit timer cannot fire on the real theme after the patch is gone. `reposition` gets fake arms, and `_H_ALGN`, `_V_ALGN` a row per arm found by `key.name`, so `Align` is not imported.

- [ ] **Step 3: Run alone, show the diff, commit on approval**

`test/widgets: one module per file`

## Task 8: `test_app_state.py`, `test_format_result.py`, readability

**Files:**
- Create: `tests/py/unit/ui/test_app_state.py`, `test_format_result.py`, `test_theme_readability.py`
- Delete, once empty: `tests/py/unit/ui/test_theme_colors.py`, `test_color_scheme.py`
- Modify: `tests/py/unit/ui/conftest.py`

**Builds on:** `tmp_settings` and the four theme tests of `test_color_scheme.py`, `_luminance` and `_contrast` of `test_theme_colors.py`.

- [ ] **Step 1: `test_app_state.py`, with `custom_themes` patched and an invented theme name in place of `"retro"`**

- [ ] **Step 2: `test_format_result.py`**

Plain numbers, and `tcalc.ui.controller.utils.calc_native` patched to `SimpleNamespace(Collection=FakeCollection, Rational=FakeRational, BigReal=FakeBigReal, ...)`.

- [ ] **Step 3: `test_theme_readability.py`**

`place` lambdas become dotted paths, read with `attrgetter`: `param("memory.text.color", id="memory")`. `user_themes_dir` is patched in the file.

- [ ] **Step 4: Remove `_user_themes` from `tests/py/unit/ui/conftest.py`**

Only the two environment lines stay. Each file runs alone after it: a test that now sees the machine's user folder is a test to fix, not a reason to put the fixture back.

- [ ] **Step 5: Run alone, show the diff, commit on approval**

`test/ui: app state and format_result alone, readability in its own file`

## Task 9: The whole check

**Files:**
- Modify: `docs/superpowers/findings/python-test-layers.md`

- [ ] **Step 1: Check the whole**

```bash
for f in tests/py/unit/ui/test_*.py; do PYTHONPATH=src .venv/bin/python -m pytest "$f" -q | tail -1; done
PYTHONPATH=src .venv/bin/python -m pytest $(ls -r tests/py/unit/ui/test_*.py) -q | tail -1
make py-test PYTEST_ARGS=-q py-lint typecheck
grep -rnE '"(kitty|retro|sponge)"|write_theme|lambda t:' tests/py/unit/ui
grep -rnE '^from tcalc\.[a-z_.]+ import \(?[A-Z]' tests/py/unit/ui
```

Expected: all pass, the first grep finds only `test_theme_readability.py`, the second only a class under test.

- [ ] **Step 2: Run the app once, record the counts in the finding, show the diff, commit on approval**

`docs/findings: the unit layer after the split`
