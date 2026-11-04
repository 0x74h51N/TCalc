# Theme Areas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A theme sets everything about a UI area in that area's table, laid over the defaults in `look.toml` by `override`, with no name mapping; then the history, memory, dock, tab and option settings of #197.

**Architecture:** `look.toml` holds every themable default under one table per area, read by the new `look.py` into a `Look` dataclass; `config.toml` keeps what no theme may touch. `Theme.look` is `override(default look, the theme's area tables)`, and the stylesheet substitutes every look field as `$<area>_<field>`.

**Tech Stack:** Python 3.14, PySide6, TOML (`tomllib`), pytest.

**Spec:** `docs/superpowers/specs/2026-11-04-theme-areas-design.md`

## Global Constraints

- A value is in `look.toml` when it is a color, a font size, a radius or a padding inside a widget's box; everything else stays in `config.toml`.
- A look field is a color place exactly when its name is `color` or ends in `_color` (`look.is_color_place`); its value is a theme color name.
- Every look field is substituted in QSS as `$<area>_<field>`; no other substitution exists.
- No value changes. Part 1 leaves every bundled theme's built stylesheet byte for byte the same (the hash pins in `tests/py/unit/ui/test_theme_overrides.py` do not change).
- A commit step stops for the owner's approval of the diff (`docs/rules/ai/git.md`). Run `make py-lint-fix` before each commit. Run single test files with `PYTHONPATH=src python -m pytest <file>`; `make py-test` once at the end of each part.
- Three PRs: Part 1, Part 2, Part 3, each from its own branch off `master` after the previous one merged. The spec and this plan go into Part 1's PR as its first commit.

## Review Focus

- A theme that sets one key of an area keeps the rest of the area (Task 1, Task 3).
- A theme that writes a behavior table (`[keypad.custom] spin_font_size = 20`) changes nothing and logs it (Task 3).
- A custom theme in the old format (`[spacing]`, `[color_usage]`) still loads; those tables are logged and skipped (Task 3).
- A theme whose area table names a missing color keeps the default place and logs it (Task 3).
- A theme switch after Part 2 changes the history and memory font ranges without a restart (Task 5).

## Part 1: the restructure (PR 1, branch `refactor/theme-areas`)

### Task 1: partial nested override

**Files:**
- Modify: `src/tcalc/typed_tables.py` (`override`)
- Test: `tests/py/unit/ui/test_typed_tables.py` (`test_override` table)

**Interfaces:**
- Produces: `override(obj, table, where)` overrides a nested dataclass field from a sub-table with `override(getattr(obj, key), sub, f"{where}.{key}")` instead of `build`; an unknown nested key is logged as `<where>.<key>.<sub>: unknown key`. `build` is unchanged.

- [ ] **Step 1: Give `Inner` a second field `k: int`, set `GOOD["inner"] = {"n": 2, "k": 3}` and `BUILT`'s `Inner(2, 3)`; the `applies` row of `test_override` now expects `"inner": Inner(7, 3)` from `{"inner": {"n": 7}}`. Add:**

```python
param({"inner": {"z": 1}}, {}, "theme.inner.z: unknown key", id="nested unknown key"),
param({"inner": {"n": "7"}}, {}, "theme.inner.n: expected int, got str", id="nested wrong type"),
```

- [ ] **Step 2: Run, expect `nested partial` to FAIL with `theme.inner.k: missing`**

Run: `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_typed_tables.py -q`

- [ ] **Step 3: In `_convert_keys`'s caller `override`, convert a key whose hint is a dataclass and whose value is a dict with a recursive `override`; leave `_convert` (used by `build`) as it is.**

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit** `refactor/typed-tables: override a nested table partially`

### Task 2: `look.toml` and `look.py`

**Files:**
- Create: `src/tcalc/ui/look.toml`, `src/tcalc/ui/look.py` (new module, argued in the spec: what every theme lays over, apart from `config.py`'s untouchable values)
- Test: `tests/py/unit/ui/test_look.py` (new file: the look's own checks have no existing home; `test_typed_tables.py` is the converter's)

**Interfaces:**
- Produces: `LOOK_PATH: Path`, `DEFAULT_LOOK: Look`, `type ColorPlace = Callable[[Look], str]`, `def color_places(look: Look) -> dict[str, str]` (key `"<area>_<field>"`, value the color name, for every color place), `def is_color_place(field: str) -> bool`, and one frozen slots dataclass per area below, fields in this order, types `str` for `_color` and family fields, `int` otherwise. Values are copied from today's `config.toml`.

Areas and fields (old name in parentheses when it differs; the QSS name is `<area>_<field>`):

- `FontsLook` `[fonts]`: `family_default`, `size_default`, `family_monospace`.
- `PaletteLook` `[palette]`: `window_color`, `window_text_color`, `base_color`, `text_color`, `button_color`, `button_text_color`, `highlight_color`, `highlighted_text_color` (all `palette_*`).
- `IconsLook` `[icons]`: `color` (`icon_color`).
- `DisplayLook` `[display]`: `background_color` (`display_background_color`), `expression_text_color`, `expression_selection_color`, `expression_selection_text_color`, `expression_slot_focus_color`, `radical_line_color`, `radical_symbol_color`, `status_text_color`, `status_error_text_color`, `divider_height`, `root_border_width`, `expression_font_size`, `expr_max_pt`.
- `ResultLook` `[result]`: `text_color` (`result_text_color`), `fraction_button_color`, `fraction_button_hover_color`, `fraction_button_pressed_color`, `fraction_icon_color`, `font_size`, `max_pt`, `btn_padding`, `frac_toggle_radius`.
- `MemoryLook` `[memory]`: `button_color`, `button_text_color`, `button_hover_color`, `button_pressed_color`, `button_disabled_color`, `button_disabled_text_color` (all `memory_button_*`), `pad_y`, `pad_x` (`memory_pad_*`).
- `KeypadLook` `[keypad]`: for role in `number, operator, action, equals, trig, function, power`: `<role>_color`, `<role>_text_color`, `<role>_pressed_color` (`<role>_key_*`); `equals_border_color`, `hover_border_color`, `checked_color`, `disabled_color`, `disabled_text_color` (`key_*`), `symbol_color` (`key_symbol_color`), `radius` (`key_radius`), `button_padding`, `compact_pad_y`, `compact_pad_x`, `min_pt`, `max_pt` (`keypad_*_pt`).
- `CustomPadLook` `[custom_pad]`: `add_key_color`, `add_key_hover_color`, `spinbox_color`, `spinbox_text_color`, `spinbox_focus_border_color`, `toolbar_separator_color`, `menu_background_color`, `menu_text_color`, `menu_border_color`, `menu_selected_color`, `menu_separator_color` (`pad_*`).
- `PickerLook` `[picker]`: `background_color`, `border_color`, `list_background_color`, `text_color`, `hover_color` (`picker_*`), `font_size` (`picker_size`).
- `MenuLook` `[menu]`: `background_color`, `text_color`, `border_color`, `selected_color`, `selected_text_color`, `selected_border_color`, `disabled_text_color`, `separator_color` (`menu_*`), `constants_symbol_color` (`constants_menu_symbol_color`), the eleven `[manubar.style]` fields with `menu_padding` as `padding`, `font_size` (`menu_size`).
- `HistoryLook` `[history]`: `background_color`, `text_color`, `row_color`, `alternate_row_color`, `selected_color`, `selected_text_color` (`history_*`).
- `OptionsLook` `[options]`: `text_color`, `hover_color`, `checked_color`, `checked_text_color` (`option_*`), `radius` (`option_radius`), `padding_y`, `padding_x`.
- `IconButtonLook` `[icon_button]`: `color`, `text_color`, `hover_color`, `pressed_color`, `light_color`, `shadow_color` (`icon_button_*`), `radius`, `padding` (`icon_padding`).
- `TooltipLook` `[tooltip]`: `background_color`, `border_color`, `text_color`, `radius`, `padding` (`tooltip_*`).
- `ToastLook` `[toast]`: `text_color`, `info_color`, `warn_color`, `error_color`, `pad_y`, `pad_x`, `radius` (`border_radius`), `font_size`.
- `Look`: one field per area, named as its table (`custom_pad: CustomPadLook`).

- [ ] **Step 1: Write `tests/py/unit/ui/test_look.py`**

```python
def test_color_places_are_str():
    for area in dataclasses.fields(Look):
        table = getattr(DEFAULT_LOOK, area.name)
        for f in dataclasses.fields(table):
            if f.name.endswith("_color"):
                assert type(getattr(table, f.name)) is str, f.name

@pytest.mark.parametrize("variant", ["light", "dark"])
def test_builtin_themes_have_every_color_place(variant):
    colors = tomllib.loads((BUILT_IN_DIR / f"{variant}.toml").read_text())["colors"]
    assert [c for c in color_places(DEFAULT_LOOK).values() if c not in colors] == []

def test_qss_names_are_unique():
    names = [
        f"{a.name}_{f.name}"
        for a in dataclasses.fields(Look)
        for f in dataclasses.fields(getattr(DEFAULT_LOOK, a.name))
    ]
    assert [n for n, k in Counter(names).items() if k > 1] == []
```

- [ ] **Step 2: Run, expect FAIL on import (`tcalc.ui.look` missing)**

- [ ] **Step 3: Write `look.toml` (the areas above, comments carried over from `config.toml`) and `look.py`.** Nothing reads them yet.

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit** `refactor/theme: add the look tables beside the config`

### Task 3: switch to the look, remove the flat names

One task because the old and new paths cannot both feed the stylesheet: the hash pins hold only when the theme loader, the substitutions, the QSS names, the readers and the bundled themes change together.

**Files:**
- Modify: `src/tcalc/theme.py`, `src/tcalc/ui/styles.py`, `src/tcalc/ui/config.py`, `src/tcalc/ui/config.toml`, the eight `*.qss` files under `src/tcalc/ui/`, `src/tcalc/themes/{kitty,retro,sponge}/theme.toml`, and the readers: `ui/utils.py`, `ui/widgets/utils.py`, `ui/widgets/math/math_primitives.py`, `ui/widgets/math/painter/symbol_icon.py`, `ui/widgets/common/button.py`, `ui/widgets/common/constants_menu.py`, `ui/widgets/calc/display/display.py`, `ui/widgets/calc/display/expression/expression.py`, `ui/widgets/calc/display/result/result.py`, `ui/widgets/calc/topbar/topbar.py`, `ui/widgets/keypad/keypad.py`, `ui/widgets/history/history.py`, `ui/widgets/history/style.py`, `ui/widgets/keypad/custom_pad.py`
- Test: `tests/py/unit/ui/test_theme_overrides.py`, `tests/py/unit/ui/test_theme_colors.py`, `tests/py/unit/ui/test_icons.py`, `tests/py/unit/ui/test_styles.py`, `tests/py/unit/ui/test_color_scheme.py`, `tests/py/unit/ui/test_typed_tables.py` (its `wrong type` row edits `c["toast"]`, which leaves `config.toml`: use `c["side_panel"].update(margin="6")`, message `config.side_panel.margin: expected int, got str`)

**Interfaces:**
- Consumes: Task 1 `override`, Task 2 `Look`, `DEFAULT_LOOK`, `ColorPlace`, `color_places`.
- Produces: `Theme.look: Look` (replaces `Theme.ui`); `get_icon(name, tint: ColorPlace | None)` and `theme_symbol_icon(symbol, place: ColorPlace)` take a `Look` selector (`lambda look: look.result.fraction_icon_color`). `CONFIG` keeps `window`, `icons` (`untinted`), `side_panel`, `history` (`max_items`, `style`, `math`), `memory`, `keypad`, `calc` (`layout`, `display` = `margin`, `spacing`, `expression_height_factor`, `expression_min_height`, `scroll_anim_duration`, `scroll_anim_curve`; `display.result` = `height`, `font_norm`, `resize_debounce_ms`, `btn_size`, `frac_icon`, `decimal_icon`; `topbar` = `side_margin`, `top_margin`, `bottom_margin`, `grid_spacing`, `spacer_stretch`), `manubar.preset`. `Result(parent, config: ResultConfig)` reads its look from `get_theme().look.result`. `custom_pad._spin_font` takes its family from `DEFAULT_LOOK.fonts.family_default`: the default look, never the theme's (#106).

- [ ] **Step 1: Rewrite the `test_theme_overrides.py` cases for area tables**

The `test_broken_part_falls_back` rows use area tables (`[[keypad]]` for the array case, `[picker]\ntext_color = "nope"` for the missing color, logged as `theme user.picker.text_color: 'nope' is not one of its colors`), read `t.look.*`, and end with `assert load_theme("dark").look == DEFAULT_LOOK`. Add:

```python
param('[keypad]\nradius = 7\n', lambda t: (t.look.keypad.radius, t.look.keypad.min_pt), (7, DEFAULT_LOOK.keypad.min_pt), "", id="one key of an area"),
param('[keypad.custom]\nspin_font_size = 20\n', lambda t: t.look.keypad, DEFAULT_LOOK.keypad, "theme user.keypad.custom: unknown key", id="behavior table"),
param('[spacing]\nkey_radius = 7\n', lambda t: t.look, DEFAULT_LOOK, "theme user.spacing: unknown key", id="old format"),
```
`test_spacing_override_reaches_stylesheet_and_python` becomes `[result]\nfrac_toggle_radius = 40\n[keypad]\nradius = 7\n`. Delete `test_stylesheet_names_are_unique` (Task 2 has it) and `test_no_stylesheet_table_read_through_config`. Keep `test_bundled_themes_style_unchanged` and its hashes untouched. `test_theme_colors.py::test_builtin_themes_have_every_color_usage_color` is deleted (Task 2 has it).

- [ ] **Step 2: Run the file, expect FAIL (`Theme` has no `look`)**

- [ ] **Step 3: `Theme.__init__`: `self.look = override(DEFAULT_LOOK, {k: v for k, v in data.items() if k not in ("name", "base", "colors", "pictures")}, where)`, then each `color_places` entry missing from `self.colors` is logged and reset to `DEFAULT_LOOK`'s choice. Delete `ui`, `_spacing`, `_replaced`, `_color_usage`.**

- [ ] **Step 4: `styles._build_subs` returns `{f"{area}_{field}": (theme.colors[v] if field.endswith("_color") else str(v)) ...}` over `Look`; `_build_palette` and `_app_font` read `look.palette` and `look.fonts`. Rename every `$name` in the QSS files to its `$<area>_<field>`.**

- [ ] **Step 5: Move the readers to `get_theme().look.<area>` or `CONFIG`, per Interfaces; delete from `config.py` and `config.toml` what the spec's Removed list names, including the seven unread history keys.**

- [ ] **Step 6: Convert `kitty`, `retro`, `sponge`: `[fonts]` keeps the three app fields, `keypad_*_pt` go to `[keypad] min_pt`/`max_pt`, `picker_size` to `[picker] font_size`, `menu_size` to `[menu] font_size`, `[spacing]` radii to `[keypad] radius`, `[icon_button] radius`, `[tooltip] radius`, `[options] radius`, `[result] frac_toggle_radius`, sponge's `[color_usage] picker_text_color` to `[picker] text_color`.**

- [ ] **Step 7: Run, expect PASS with the hash pins unchanged**

Run: `PYTHONPATH=src python -m pytest tests/py/unit/ui -q && make typecheck`
Expected: all pass; `git diff tests/py/unit/ui/test_theme_overrides.py` shows no hash change.

- [ ] **Step 8: Run `make py-test`; open the app with each bundled theme and compare it with `master`.**

- [ ] **Step 9: Commit** `refactor/theme: one table per area in look.toml, no flat override names`

### Task 4: template and findings

**Files:**
- Modify: `src/tcalc/themes/theme-template.toml`, `docs/superpowers/findings/typed-config.md`

- [ ] **Step 1: The template lists each area table with its fields commented out and their defaults, says a theme file is a partial `look.toml`, and drops the `[spacing]` and `[color_usage]` sections.**

- [ ] **Step 2: Update the 2026-11-02 entry of `typed-config.md` to the new flow (look.toml, `Theme.look`, `$<area>_<field>`), deleting what is no longer true.**

- [ ] **Step 3: Commit** `docs/theme: describe the area tables`

## Part 2: history and memory (PR 2, branch `feat/theme-history-memory`)

### Task 5: history and memory font sizes in the look

**Files:**
- Modify: `look.toml`, `look.py`, `config.toml`, `config.py`, `ui/widgets/side_panel/side_panel.py`, `ui/window.py`, `ui/widgets/history/history.py`, `ui/widgets/history/style.py`
- Test: `tests/py/ui/test_theme_switch.py`

**Interfaces:**
- Produces: `HistoryLook` gains `font_size`, `max_pt`, `expr_min_pt`, `expr_max_pt`, `clear_min_pt`, `clear_max_pt` (`clr_btn_*`), `action_btn_size`, `math_font_size` (`[history.math] base_font`); `MemoryLook` gains `font_size`, `max_pt`. `SidePanel.register_font_targets(targets, sizes: Callable[[Look], tuple[int, int]], callback=None)`: the range is resolved from `get_theme().look` each time fonts are applied.

- [ ] **Step 1: Test in `test_theme_switch.py`: with a written theme `[history]\nfont_size = 11\nmax_pt = 11\n`, `apply_theme` to it and back to dark; the history list's `font().pointSize()` is 11, then the dark value.**
- [ ] **Step 2: Run, expect FAIL (the range is fixed at registration)**
- [ ] **Step 3: Move the fields, change `register_font_targets` and its three callers in `window.py`, read the rest through `get_theme().look.history`**
- [ ] **Step 4: Run the file and `tests/py/ui/test_history.py`, expect PASS; hash pins unchanged**
- [ ] **Step 5: Commit** `feat/theme: history and memory font sizes in the theme`

### Task 6: history colors and sizes per part

**Files:**
- Modify: `look.toml`, `look.py`, `ui/widgets/history/history.py`, `ui/widgets/history/style.qss`, `ui/widgets/common/button.py` (`OptionGroup` takes its look)
- Test: `tests/py/ui/test_history.py`

**Interfaces:**
- Produces: `HistoryLook` gains `expression_color`, `result_color` (default `text_secondary`, today's list color), `result_min_pt`, `result_max_pt` (defaults the list's `font_size` and `max_pt`), `item_button_color` (icon tint, default `icon`), `mode_text_color`, `mode_checked_color`, `mode_checked_text_color`, `mode_font_size` (defaults `[options]`'s and `size_default`), `clear_text_color`, `clear_color` (defaults `[icon_button]`'s). `OptionGroup(..., look: OptionsLook)`: the history passes one built from the `mode_*` fields, the top bar passes `look.options`.

- [ ] **Step 1: Params in `test_history.py`: a theme setting each new field reaches its widget (label palette/stylesheet color, label font size, icon tint by `test_icons._opaque_color`), and the default theme renders as before**
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement; QSS selectors on `#historyItem` and the clear button's object name**
- [ ] **Step 4: Run, expect PASS; diff the built stylesheets against Part 1 and update the pins only for the added rules**
- [ ] **Step 5: Commit** `feat/theme: history expression, result, buttons and modes in the theme`

## Part 3: docks, tabs and options (PR 3, branch `feat/theme-docks-tabs`)

### Task 7: dock title, tab bar, option font size

**Files:**
- Modify: `look.toml`, `look.py`, `ui/widgets/common/dock_title_bar.py`, `ui/styles/common.qss`, `ui/widgets/common/button.py`
- Test: `tests/py/ui/test_theme_switch.py`

**Interfaces:**
- Produces: `DockLook` `[dock]`: `title_color` (default `text_primary`), `title_font_size` (default `size_default`'s value). `TabsLook` `[tabs]`: `background_color` (`background`), `text_color` (`text_primary`), `selected_color` (`background_light`), `hover_color` (`selection_background`), `radius` (2), `font_size` (9). `OptionsLook.font_size` (9). QSS: `QTabBar` rules in `common.qss`; `DockTitleBar`'s label gets an object name the dock rule selects.

- [ ] **Step 1: Tests: a theme's `[dock]` and `[options]` values reach a `DockTitleBar` label and an `OptionGroup` button after `apply_theme`; a stylesheet built with `[tabs] radius = 5` contains the `QTabBar::tab` rule with `5px`**
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS; diff the built stylesheets and update the pins for the added rules only; open the app, tabify two docks and look in each bundled theme**
- [ ] **Step 5: Update `theme-template.toml` for Parts 2 and 3's fields; commit** `feat/theme: dock titles, dock tabs and option font size in the theme`
