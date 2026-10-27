# Theme Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** View > Theme with Light, Dark, System Default (live switch, persisted), and a disabled Add Custom Theme entry.

**Architecture:** Qt holds the scheme (`QStyleHints.setColorScheme`), `colorSchemeChanged` is the only trigger. Its handler loads the matching color set (only that one is kept in memory) and sets the app palette and the one application stylesheet (every `.qss` in the UI); Qt propagates both to all widgets. Icons come from a `QIconEngine` that draws for the active theme at paint time. Widgets hold no theme code. `AppState` only persists the user's choice.

**Tech Stack:** Python 3.14, PySide6 6.12 (Qt Widgets), tomllib, pytest + pytest-qt (offscreen).

**Spec:** `docs/superpowers/specs/2026-10-27-theme-switching-design.md`

## Global Constraints

- Qt APIs and Qt-recommended patterns first; no custom theming framework, no new module just for theming.
- Only the active color set is held in memory; the other is read from `config.toml` only on a switch.
- No polling, no timers; react to `QStyleHints.colorSchemeChanged` only.
- Widgets and style modules hold no theme code: no per-widget color stylesheets or palettes, no refresh hooks. Qt's app palette, app stylesheet and the icon engine carry a switch.
- Alpha colors are fixed `rgba(r, g, b, a%)` values in each color set; no color is computed in Python. No `Any` in type hints.
- SVGs: copy from an icon set unmodified; style-only tweaks (color, stroke width) only where this plan says so, path data never touched, every modified file noted in `assets/icons/README.md`.
- Existing dark look must not change, except `spin_text` (`#f0f2ff` -> `#f6f7fb`, invisible), the toast alpha (140/255 -> 55%, invisible), and disabled keypad keys, whose disabled colors never applied (`key_disabled_bg = "disabled_bg"` resolved to the literal string `disabled_bg`) and now do.
- Tests run offscreen (`tests/py/unit/ui/conftest.py`), where `setColorScheme` is ignored: test the scheme handler by calling it with a `Qt.ColorScheme`, and test that the menu requests the right scheme by patching `QStyleHints.setColorScheme`.
- Every commit: run `make py-lint`, `make typecheck`, `make py-test`; push the branch after committing.

## Review Focus

1. Theme switched while a hidden dock (e.g. history) is closed: when reopened it must show the new theme. (App stylesheet and palette reach hidden widgets; Task 5 test pins it.)
2. Switching back and forth must not stack stylesheets (`apply_styles` used to append to `app.styleSheet()`). (Task 3 test.)
3. Stored value from an older or edited config (`"blue"`, empty) must fall back to System Default, not crash. (Task 3 test.)
4. Under System Default with an OS that reports `Unknown` (WSLg without gtk3), the app must come up Dark. (Task 3 test.)
5. Custom pad keys with user-picked colors keep those colors across switches. (Task 5 test.)
6. Moving keypad QSS to app level must not leak onto other widgets: top bar memory buttons (also `keypadRole`), every `QSpinBox`, every `QFrame`. (Task 5 scoping + test.)

---

### Task 1: Color sets

**Files:**
- Modify: `src/tcalc/config.toml` (`[theme.colors]` -> `[theme.dark.colors]`, add `[theme.light.colors]`, add 4 keys to both)
- Modify: `src/tcalc/theme.py`
- Modify: `src/tcalc/ui/config.toml` (remaps below)
- Test: `tests/py/unit/ui/test_theme_colors.py`

**Interfaces:**
- Produces: `Theme.variant: str` (`"dark"` | `"light"`); `load_theme(variant: str) -> Theme` in `tcalc/theme.py` replaces the singleton with a `Theme` holding only that variant's colors; `get_theme()` unchanged (defaults to `"dark"`). `Theme.spacing` / `Theme.fonts` still come from `[theme.spacing]` / `[theme.fonts]`.

New keys (both sets): `control`, `control_hover`, `control_accent`, `icon`.

Light values (hand-written from the dark ones; button families copied from dark unchanged):

| key | dark (existing / new) | light |
|---|---|---|
| background | #1E1E1E | #F4F5F7 |
| background_dark | #1E1E1E | #FFFFFF |
| background_dark_alt | #242424 | #F7F8FA |
| background_medium | #2a2c33 | #ECEDF1 |
| background_light | #3f4450 | #DCDFE6 |
| foreground | #f6f7fb | #1E1F24 |
| text_primary | #f6f7fb | #1E1F24 |
| text_secondary | #b6b8c9 | #4A4D57 |
| text_muted / text_tertiary | #808290 | #7A7D88 |
| border_default | #111111 | #C4C7CF |
| border_light | #444957 | #D5D8DF |
| border_focus | #5a606d | #8A8F9C |
| border_dark | #111111 | #B4B8C2 |
| status_warn | #e0a828 | #B7791F |
| status_error | #d94040 | #C62828 |
| status_info | #a6c7ff | #2B6CB0 |
| status_success | #9bdc8c | #2F855A |
| selection_background | #3a3d47 | #D6DEEE |
| selection_text | #ffffff | #1E1F24 |
| control (new) | #343842 | #DCDFE6 |
| control_hover (new) | #2a2c33 | #E6E8ED |
| control_accent (new) | #f3d199 | #9A6B12 |
| icon (new) | #fcfcfc | #232629 |

Remaps in `src/tcalc/ui/config.toml` (non-keypad uses of button colors, spec 1a; dark values are identical, so dark doesn't change):
- `[style.option_group]` `checked_base` accent -> control; `hover_base` secondary_hover -> control_hover
- `[keypad.custom.colors]` `spin_bg`, `separator`, `toolbar_separator`, `add_button_bg` accent -> control; `add_button_hover_bg` secondary_hover -> control_hover; `spin_text` secondary_text -> text_primary; `spin_focus_border` accent_text -> control_accent
- `[calc.style.colors]` `disabled_bg` secondary_hover -> control_hover; `disabled_text` accent_text -> control_accent
- `[calc.display.result.colors]` `frac_bg*` accent -> control; `frac_icon` accent_text -> control_accent
- `[calc.topbar.memory_colors]` `memory_bg*` accent -> control; `memory_disabled_bg` secondary_hover -> control_hover; `memory_disabled_text` accent_text -> control_accent

- [ ] **Step 1: Write the failing tests**

```python
def test_default_is_dark_and_unchanged():
    t = load_theme("dark")
    assert t.variant == "dark"
    assert t.colors["background"] == "#1E1E1E" and t.colors["accent"] == "#343842"

def test_light_loads_only_light():
    t = load_theme("light")
    assert t.variant == "light" and get_theme() is t
    assert t.colors["background"] == "#F4F5F7"
    assert t.colors["primary"] == load_theme("dark").colors["primary"]  # button family kept

def test_sets_have_identical_keys():
    assert load_theme("light").colors.keys() == load_theme("dark").colors.keys()

def test_new_keys_match_old_dark_values():
    c = load_theme("dark").colors
    assert (c["control"], c["control_hover"], c["control_accent"]) == (c["accent"], c["secondary_hover"], c["accent_text"])
```
Plus a test that no `ui/config.toml` entry listed in the remaps above still names `accent`, `accent_text` or `secondary_hover`. Reset to `load_theme("dark")` in a fixture so other tests keep dark.

- [ ] **Step 2: Run, expect FAIL** — `PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/ui/test_theme_colors.py -q` → ImportError on `load_theme`.
- [ ] **Step 3: Implement** the config split, the light set, the 4 new keys, the remaps, `Theme(variant)` and `load_theme`.
- [ ] **Step 4: Run, expect PASS**, then the full suite (`make py-test`) still green.
- [ ] **Step 5: Commit** `feat/theme: light and dark color sets` and push.

### Task 2: Icons follow the theme

**Files:**
- Modify: `src/tcalc/ui/utils.py` (`get_icon`)
- Modify: `src/tcalc/ui/config.toml` (new `[icons]` table)
- Create: `assets/icons/light/snap-angle-symbolic.svg`, `assets/icons/light/application-exit.svg`
- Modify: `assets/icons/README.md`
- Test: `tests/py/unit/ui/test_icons.py`

**Interfaces:**
- Consumes: `get_theme().variant`, `get_theme().colors["icon"]` (Task 1).
- Produces: `get_icon(name: str, tint: str | None = None) -> QIcon` — same signature. Resolution: file = `assets/icons/<variant>/<name>.svg` if it exists, else `assets/icons/<name>.svg`; tint = the given `tint`, else `None` if `name` is in `[icons].untinted`, else `colors["icon"]`.
- `[icons] untinted = ["accessories-calculator", "application-exit", "edit-delete", "edit-delete-shred", "snap-angle-symbolic"]` (multi-color and red icons).

Light files: get Breeze light from the Ubuntu package (`apt-get download kf6-breeze-icon-theme`, `dpkg-deb -x` into a scratch dir; files under `usr/share/icons/breeze/`).
- `application-exit.svg`: copy unmodified (`actions/22/`), prove with `cmp`.
- `snap-angle-symbolic.svg` (`actions/22/`): copy, then the same style-only tweak the dark file has (user-approved): in each path `style`, `stroke:none` -> `stroke:currentColor; stroke-width:1; stroke-linejoin:round`; recolor `.ColorScheme-Accent` to light `text_secondary` `#4A4D57`. Diff the `d="..."` data against the original: must be identical.
- README: a "light/" section listing both, the angle one marked modified like the dark one.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.usefixtures("qapp")
def test_single_color_icon_is_tinted_with_theme_icon_color(): ...
    # load_theme("light"); pixel at an opaque point of get_icon("edit-copy").pixmap(32) == QColor("#232629")
def test_untinted_icons_keep_their_colors(): ...
    # edit-delete opaque pixel stays red (#da4453) in both variants
def test_light_variant_file_is_used(): ...
    # load_theme("light"): get_icon("snap-angle-symbolic") renders like assets/icons/light/snap-angle-symbolic.svg, not the dark file
def test_dark_has_no_variant_dir_and_falls_back(): ...
```
Keep the existing bundle/menu-icon tests passing.

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** `[icons]`, `get_icon` resolution, the two light files, README.
- [ ] **Step 4: Run, expect PASS**; full suite green.
- [ ] **Step 5: Commit** `feat/theme: icons follow the theme` and push.

### Task 3: Scheme state, startup and app-level styling

**Files:**
- Modify: `src/tcalc/theme.py` (add `ThemeMode`)
- Modify: `src/tcalc/app_state.py` (persisted `theme_mode`)
- Modify: `src/tcalc/ui/styles.py` (`apply_styles` sets instead of appending; `apply_color_scheme`)
- Modify: `src/tcalc/ui/app.py` (startup wiring)
- Modify: `scripts/dev` (WSL only: `export QT_QPA_PLATFORMTHEME=gtk3` unless already set; detect via `/proc/version` containing `microsoft`)
- Test: `tests/py/unit/ui/test_color_scheme.py`

**Interfaces:**
- Produces:
  - `class ThemeMode(StrEnum): LIGHT = "light"; DARK = "dark"; SYSTEM = "system"` with property `scheme -> Qt.ColorScheme` (Light / Dark / Unknown).
  - `AppState.theme_mode: ThemeMode` property; setter persists QSettings key `"theme"`; unknown/missing stored value -> `ThemeMode.SYSTEM`.
  - `apply_color_scheme(app: QApplication, scheme: Qt.ColorScheme) -> None` in `ui/styles.py`: `load_theme("light" if scheme == Qt.ColorScheme.Light else "dark")`, then `apply_styles(app)`; Task 4 extends it with the widget pass.
  - `apply_styles(app)` sets `app.setStyleSheet(common_qss)` (no append), keeps Fusion + palette.
- `run_app` order: create app → `hints = app.styleHints()` → `hints.colorSchemeChanged.connect(lambda s: apply_color_scheme(app, s))` → `hints.setColorScheme(get_app_state().theme_mode.scheme)` → `apply_color_scheme(app, hints.colorScheme())` (covers no signal when the scheme is already the requested one) → build window.

- [ ] **Step 1: Write the failing tests**

```python
def test_mode_maps_to_qt_scheme():
    assert [m.scheme for m in ThemeMode] == [Qt.ColorScheme.Light, Qt.ColorScheme.Dark, Qt.ColorScheme.Unknown]

def test_theme_mode_persists_and_bad_value_falls_back(tmp_settings): ...
    # set LIGHT -> new AppState reads LIGHT; QSettings "theme"="blue" -> SYSTEM

def test_light_scheme_sets_light_palette(qapp):
    apply_color_scheme(qapp, Qt.ColorScheme.Light)
    assert qapp.palette().color(QPalette.ColorRole.Window) == QColor("#F4F5F7")

def test_unknown_scheme_is_dark(qapp):
    apply_color_scheme(qapp, Qt.ColorScheme.Unknown)
    assert get_theme().variant == "dark"

def test_reapplying_does_not_stack_stylesheet(qapp):
    apply_color_scheme(qapp, Qt.ColorScheme.Light); n = len(qapp.styleSheet())
    apply_color_scheme(qapp, Qt.ColorScheme.Dark); apply_color_scheme(qapp, Qt.ColorScheme.Light)
    assert len(qapp.styleSheet()) == n
```
(`tmp_settings`: point QSettings at a temp dir with `QSettings.setPath` / `setDefaultFormat(IniFormat)` in the fixture; reset the `AppState` singleton.) Restore dark + original palette/stylesheet after each test, as `test_styles.py` does.

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** as in Interfaces.
- [ ] **Step 4: Run, expect PASS**; full suite green; `bash -n scripts/dev`.
- [ ] **Step 5: Commit** `feat/theme: follow Qt's color scheme at startup and on change` and push.

### Task 4: Fixed alpha colors, QSS names theme keys

**Files:**
- Modify: `src/tcalc/config.toml` (new keys in both sets, below)
- Modify: `src/tcalc/ui/config.toml` (delete `checked_base/alpha`, `hover_base/alpha` in `[style.option_group]`; `alpha`, `*_base` in `[toast]`; `[calc.style.colors]`; `[calc.display.result.colors]`; `[calc.topbar.memory_colors]`; `[keypad.custom.colors]`; the color references in `[manubar.style]`; add `frac_icon_tint = "control_accent"` to `[calc.display.result]`)
- Modify: every `.qss` under `src/tcalc/ui` to name theme keys directly (`$custom_key_bg` -> `$secondary`, `$menu_background` -> `$background_medium`, `$memory_bg` -> `$control_bg`, `$status_info` in result -> `$text_secondary`, ...), using the mappings the deleted tables hold today
- Modify: `src/tcalc/ui/styles.py`, `ui/widgets/keypad/style.py`, `ui/widgets/calc/topbar/style.py`, `ui/widgets/calc/display/result/style.py`, `ui/manubar/style.py` (drop the alpha loops and indirection loops); `src/tcalc/ui/utils.py` (delete `rgba`); `ui/widgets/calc/display/result/result.py` (tint key from `frac_icon_tint`); `ui/widgets/keypad/custom_pad.py` (color picker lists only values `QColor.isValidColorName` accepts, so `rgba()` entries are skipped)
- Test: `tests/py/unit/ui/test_theme_colors.py`

New keys (dark = what today's pairs produce; light hand-written):

| key | dark | light |
|---|---|---|
| control_bg | rgba(52, 56, 66, 20%) | rgba(30, 31, 36, 6%) |
| control_bg_hover | rgba(52, 56, 66, 28%) | rgba(30, 31, 36, 10%) |
| control_bg_pressed | rgba(52, 56, 66, 38%) | rgba(30, 31, 36, 16%) |
| control_disabled_bg | rgba(42, 44, 51, 10%) | rgba(30, 31, 36, 4%) |
| control_disabled_text | rgba(243, 209, 153, 30%) | rgba(154, 107, 18, 40%) |
| option_checked_bg | rgba(52, 56, 66, 25%) | rgba(30, 31, 36, 10%) |
| option_hover_bg | rgba(42, 44, 51, 35%) | rgba(30, 31, 36, 6%) |
| toast_info_bg | rgba(63, 68, 80, 55%) | rgba(220, 223, 230, 90%) |
| toast_warn_bg | rgba(224, 168, 40, 55%) | rgba(183, 121, 31, 25%) |
| toast_error_bg | rgba(217, 64, 64, 55%) | rgba(198, 40, 40, 20%) |

`frac_bg*` and `memory_bg*` were the same pairs and both become `control_bg*`; `disabled_*` and `memory_disabled_*` both become `control_disabled_*`.

- [ ] **Step 1: Write the failing tests**

```python
def test_no_alpha_pairs_left_in_ui_config():
    # no value in ui/config.toml is a [str, float] pair
def test_alpha_helper_is_gone():
    assert not hasattr(tcalc.ui.utils, "rgba")
def test_dark_alpha_values_match_old_look():
    assert load_theme("dark").colors["control_bg"] == "rgba(52, 56, 66, 20%)"
def test_every_qss_placeholder_resolves():
    # for every .qss under src/tcalc/ui: load_qss(path) contains no "$"
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, expect PASS**; full suite green.
- [ ] **Step 5: Commit** `refactor/theme: fixed alpha colors, QSS names theme keys` and push.

### Task 5: One application stylesheet, palette roles

**Files:**
- Modify: `src/tcalc/ui/styles.py`: `apply_styles(app)` sets `app.setStyleSheet` to every `.qss` under `src/tcalc/ui` (sorted by path, `common.qss` first), substituted by `build_subs()`; `build_subs()` returns theme colors + spacing + the scalar config values the templates use; `Base` = `background_dark` stays in `_build_palette`.
- Modify: `ui/widgets/keypad/style.qss`: scope keypad rules to `QWidget[uiRole="keypad"]` descendants, `QSpinBox` -> `KSSpinBox`, `QFrame` -> `QWidget[uiRole="keypad"] QFrame`; `keypad.py` and `custom_pad.py` set `uiRole="keypad"` on themselves.
- Modify: remove widget-level color stylesheets and palettes: `manubar/menu.py`, `keypad/keypad.py`, `keypad/custom_pad.py`, `calc/topbar/topbar.py`, `calc/display/display.py`, `calc/display/result/result.py`, `history/history.py` (keeps its non-color setup), `side_panel/side_panel.py`. Display, result and side panel: `setBackgroundRole(QPalette.ColorRole.Base)` + `setAutoFillBackground(True)`. Delete style modules left with nothing to do.
- Modify: `ui/widgets/common/toaster.py`: set the `toastLevel` property and re-polish; no inline sheet, no `_bg_for_level`, no `_TOAST_ALPHA`; `toaster.qss` gets the toast config scalars via `build_subs`.
- Remove the duplicate `#radicandSlot` rule.
- Test: `tests/py/ui/test_theme_switch.py`

- [ ] **Step 1: Write the failing tests** (MainWindow with isolated settings)

```python
def test_widgets_have_no_color_stylesheets(window):
    # every widget's own styleSheet() is "" (user-colored custom keys excepted)
def test_switch_reaches_open_and_hidden_widgets(qapp, window):
    apply_color_scheme(qapp, Qt.ColorScheme.Light)
    # side panel / display background == #FFFFFF; a hidden SidePanel too
    # app stylesheet contains the light background_dark and no "$"
def test_memory_buttons_get_no_keypad_rules(): ...   # Review Focus 6: keypad rules are scoped
def test_user_key_colors_survive_switch(qapp, window): ...  # Review Focus 5
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, expect PASS**; full suite green.
- [ ] **Step 5: Commit** `feat/theme: one application stylesheet, widgets follow the palette` and push.

### Task 6: Icons drawn for the active theme

**Files:**
- Modify: `src/tcalc/ui/utils.py`: `get_icon(name: str, tint_key: str | None = None) -> QIcon` returns `QIcon(_ThemeIconEngine(build))`; `build` loads the variant file and tints it (with `colors[tint_key]`, else `colors["icon"]` unless untinted) as Task 2 does. `_ThemeIconEngine(QIconEngine)` keeps the icon built for the theme object it last saw and rebuilds when `get_theme()` returns another one; `paint`, `pixmap`, `scaledPixmap`, `isNull` delegate to that icon; `clone` copies.
- Modify: `ui/widgets/common/button.py` (`IconButton(tint_key=...)` instead of a hex `tint`), `ui/widgets/calc/display/result/result.py`, `ui/widgets/common/constants_menu.py` (symbol icons through the same engine, built with `text_primary`).
- Test: `tests/py/unit/ui/test_icons.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_shown_icon_follows_a_switch(qapp):
    icon = get_icon("edit-copy")          # dark
    load_theme("light")
    assert _opaque_color(icon) == QColor("#232629")   # same QIcon object, new tint
def test_angle_icon_switches_file(qapp): ...
def test_red_icon_stays_red_after_switch(qapp): ...
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, expect PASS**; full suite green.
- [ ] **Step 5: Commit** `feat/theme: icons draw for the active theme` and push.

### Task 7: View > Theme menu

**Files:**
- Modify: `src/tcalc/ui/manubar/defins.py` (Theme submenu first in `VIEW_ACTIONS`, then `MenuSeparatorItem()`, then Keypad Preset)
- Modify: `src/tcalc/ui/manubar/menu_builder.py` (`MenuActionItem.theme: ThemeMode | None = None`, like `preset`)
- Modify: `src/tcalc/ui/controller/menubar/view.py` (`ViewOperations.set_theme(mode: ThemeMode) -> None`: save `get_app_state().theme_mode = mode`, then `QGuiApplication.styleHints().setColorScheme(mode.scheme)`)
- Modify: `src/tcalc/ui/manubar/menus/view.py` (collect theme actions into one exclusive `QActionGroup`, check the one matching `app_state.theme_mode`)
- Test: `tests/py/unit/ui/test_theme_menu.py`

**Interfaces:**
- Consumes: `ThemeMode`, `AppState.theme_mode` (Task 3).
- Theme submenu items, in order: `Light`, `Dark`, `System Default` (checkable, `item_type=OPS`, `fn=lambda ops: ops.set_theme(ThemeMode.X)`, `theme=ThemeMode.X`), `MenuSeparatorItem()`, `Add Custom Theme...` (`enabled=False`, `fn=lambda ops: None`). Icons optional; none is fine.

- [ ] **Step 1: Write the failing tests**

```python
def test_theme_is_first_in_view_menu(main_window):
    titles = [a.text() for a in view_menu.actions()]
    assert titles[0] == "Theme" and view_menu.actions()[1].isSeparator() and titles[2] == "Keypad Preset"

def test_theme_items(main_window):
    assert [a.text() for a in theme_menu.actions() if not a.isSeparator()] == ["Light", "Dark", "System Default", "Add Custom Theme..."]
    assert not action("Add Custom Theme...").isEnabled()

def test_choosing_light_requests_qt_scheme_and_persists(main_window, monkeypatch):
    calls = []; monkeypatch.setattr(QStyleHints, "setColorScheme", lambda self, s: calls.append(s))
    action("Light").trigger()
    assert calls == [Qt.ColorScheme.Light] and get_app_state().theme_mode is ThemeMode.LIGHT
    assert action("Light").isChecked() and not action("Dark").isChecked()
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, expect PASS**; full suite green.
- [ ] **Step 5: Commit** `feat/theme: View > Theme menu` and push.

### Task 8: Manual check

- [ ] `make dev` on WSLg (gtk3 platform theme via `scripts/dev`): switch Light ↔ Dark ↔ System Default; every visible part switches, icons included; restart keeps the choice. Report to the user with what was seen; open items (colored keypad buttons on Light) go to the user, not fixed silently.
