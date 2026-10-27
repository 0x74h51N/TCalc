# Theme Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** View > Theme with Light, Dark, System Default (live switch, persisted), and a disabled Add Custom Theme entry.

**Architecture:** Qt holds the scheme (`QStyleHints.setColorScheme`), `colorSchemeChanged` is the only trigger. Its handler loads the matching color set (only that one is kept in memory), sets the app palette and app stylesheet, and re-runs the existing per-widget `apply_*_style` functions. `AppState` only persists the user's choice.

**Tech Stack:** Python 3.14, PySide6 6.12 (Qt Widgets), tomllib, pytest + pytest-qt (offscreen).

**Spec:** `docs/superpowers/specs/2026-10-27-theme-switching-design.md`

## Global Constraints

- Qt APIs and Qt-recommended patterns first; no custom theming framework, no new module just for theming.
- Only the active color set is held in memory; the other is read from `config.toml` only on a switch.
- No polling, no timers; react to `QStyleHints.colorSchemeChanged` only.
- Style modules (`*/style.py`) gain no theme code; they are re-called as they are.
- SVGs: copy from an icon set unmodified; style-only tweaks (color, stroke width) only where this plan says so, path data never touched, every modified file noted in `assets/icons/README.md`.
- Existing dark look must not change, except `spin_text` (`#f0f2ff` -> `#f6f7fb`, invisible).
- Tests run offscreen (`tests/py/unit/ui/conftest.py`), where `setColorScheme` is ignored: test the scheme handler by calling it with a `Qt.ColorScheme`, and test that the menu requests the right scheme by patching `QStyleHints.setColorScheme`.
- Every commit: run `make py-lint`, `make typecheck`, `make py-test`; push the branch after committing.

## Review Focus

1. Theme switched while a hidden dock (e.g. history) is closed: when reopened it must show the new theme. (Task 4 walks `QApplication.allWidgets()`, which includes hidden widgets; test pins it.)
2. Switching back and forth must not stack stylesheets (`apply_styles` used to append to `app.styleSheet()`). (Task 3 test.)
3. Stored value from an older or edited config (`"blue"`, empty) must fall back to System Default, not crash. (Task 3 test.)
4. Under System Default with an OS that reports `Unknown` (WSLg without gtk3), the app must come up Dark. (Task 3 test.)
5. Custom pad keys with user-picked colors keep those colors across switches. (Task 4 test.)

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

### Task 4: Open widgets re-apply their styles

**Files:**
- Modify: `src/tcalc/ui/styles.py` (widget pass inside `apply_color_scheme`)
- Modify (move inline color code into a method, no new logic): `src/tcalc/ui/widgets/side_panel/side_panel.py` (`apply_palette()`), `src/tcalc/ui/widgets/common/button.py` (`IconButton`: keep `icon_name`, take `tint_key: str | None` (theme key) instead of a hex `tint`, add `refresh_icon()`; `KeyButton.refresh_icon()` for math-rendered labels), `src/tcalc/ui/widgets/calc/display/result/result.py` (pass `tint_key`), `src/tcalc/ui/widgets/calc/topbar/topbar.py` (public `memory_widget` property)
- Modify: `src/tcalc/ui/manubar/menu_builder.py` (store `"iconName"` property on created actions and submenu actions), `src/tcalc/ui/widgets/common/constants_menu.py` (store `"mathSymbol"` property on symbol actions)
- Test: `tests/py/unit/ui/test_theme_switch_widgets.py`

**Interfaces:**
- Consumes: `apply_color_scheme` (Task 3), `get_icon` (Task 2).
- Produces: in `ui/styles.py`, one table of `(widget type, callable)` pairs, applied with `isinstance` to every widget in `QApplication.allWidgets()` (lazy imports inside the function to avoid import cycles):
  - `QMenuBar` → `apply_menu_styles`
  - `QMenu` → refresh each action's icon from its `"iconName"` (via `get_icon`) or `"mathSymbol"` (via `render_symbol(sym, QColor(colors["text_primary"]), ICON_BOX)`)
  - `Display` → `apply_display_style`; `Result` → result `apply_style`; `Keypad` and `CustomPad` → `apply_keypad_style`; `History` → `apply_history_style(w.list)`; `TopBar` → `apply_topbar_style(w.memory_widget)`; `SidePanel` → `w.apply_palette()`; `IconButton` → `w.refresh_icon()`; `KeyButton` → `w.refresh_icon()`
- Not refreshed on purpose: custom pad color-picker swatches (they list the colors of the theme active when the pad was built; picked colors are stored as hex anyway).

- [ ] **Step 1: Write the failing tests** (build a `MainWindow` offscreen, or the individual widgets)

```python
def test_switch_restyles_open_widgets(qapp, main_window):
    apply_color_scheme(qapp, Qt.ColorScheme.Light)
    assert "#F4F5F7".lower() in main_window.menuBar().styleSheet().lower() or "#ECEDF1".lower() in ...
    # keypad, display, history, topbar sheets contain light values; side panel palette background == #FFFFFF

def test_hidden_dock_is_restyled(qapp, main_window): ...   # Review Focus 1

def test_menu_action_icons_refresh(qapp, main_window): ...  # an action with iconName gets a new cacheKey after a switch

def test_custom_key_colors_survive_switch(qapp): ...        # Review Focus 5: a KeyButton styled with a user hex keeps it
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the moves and the table.
- [ ] **Step 4: Run, expect PASS**; full suite green.
- [ ] **Step 5: Commit** `feat/theme: open widgets follow a theme switch` and push.

### Task 5: View > Theme menu

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

### Task 6: Manual check

- [ ] `make dev` on WSLg (gtk3 platform theme via `scripts/dev`): switch Light ↔ Dark ↔ System Default; every visible part switches, icons included; restart keeps the choice. Report to the user with what was seen; open items (colored keypad buttons on Light) go to the user, not fixed silently.
