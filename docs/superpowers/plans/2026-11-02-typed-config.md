# Typed Config Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read every `config.toml` value, every theme override and the custom pad's saved layout as typed dataclass attributes, with theme mistakes logged and skipped instead of stopping the app.

**Architecture:** A new `typed_tables.py` turns a table into a dataclass (`build`) or applies a partial table to one (`override`). `config.py` loads `CONFIG: UiConfig`; `Theme` resolves its overrides once into `ui`, `fonts`, `color_usage` and `colors`. Widgets read `CONFIG`, except the few reads of a stylesheet table, which go through `get_theme().ui`.

**Tech Stack:** Python 3.14, PySide6, `tomllib`, `dataclasses`, `typing.get_type_hints`, pytest, pytest-qt, mypy.

**Spec:** `docs/superpowers/specs/2026-11-02-typed-config-design.md`

## Global Constraints

- No value in `config.toml` or a theme file changes; only where a value lives (the moves the spec lists).
- No default in code for a config value; a theme field optional by the theme format keeps its dataclass default.
- No string-key config read and no config cast under `src/tcalc/` at the end.
- Theme switching keeps restyling at once (`apply_theme`), with no restart.
- No em dash anywhere; Markdown not hard-wrapped; comments say why, one line.
- Every commit step stops for the human agent: show the diff, commit only after approval (`docs/rules/ai/git.md`). Run `make py-lint-fix` before it.
- Run single files with `PYTHONPATH=src python -m pytest <file>`; the whole suite only with `make py-test`.

## Review Focus

- A user theme from before this change (with `[spacing]`, `[fonts]`, `[color_usage]`, `[[pictures]]`) loads with the same look: Task 3 `test_bundled_themes_style_unchanged`.
- A theme that sets a radius in `[spacing]` still rounds the keys (`key_radius` now lives in `[style]`): Task 3 `test_spacing_override_reaches_stylesheet_and_python`.
- A pad created from the GUI (no saved layout yet) opens with the defaults and no warning, and every edit (keys, colors, removed key, cols, rows, grid rows, rename) saves and reloads as it was: Task 6 `test_new_pad_starts_from_defaults_silently` and `test_edited_layout_round_trips`; the existing pad tests in `tests/py/unit/ui/test_styles.py` and `tests/py/ui/test_theme_switch.py` stay green. A layout saved by an earlier version is not required to load.
- `bool` values are not accepted for an `int` field (bool is an int in Python): Task 1 row `bool for int`.
- A theme switch after a broken theme leaves no state behind: Task 3 `test_broken_part_falls_back` switches to the broken theme and back to Dark.

## Files

- Create `src/tcalc/typed_tables.py`: `build`, `override`, `TableError`. Its one job: convert a table into a dataclass by its fields.
- Modify `src/tcalc/ui/config.py`: dataclasses, `CONFIG`, `STYLESHEET_TABLES`.
- Modify `src/tcalc/ui/config.toml`, `src/tcalc/themes/light.toml`, `dark.toml`, `theme-template.toml`.
- Modify `src/tcalc/theme.py`, `src/tcalc/ui/styles.py`, the two QSS files using `$menu_font_size`, `$picker_font_size`.
- Modify every module that imports from `tcalc.ui.config` (20 under `src/tcalc/`, 3 tests).
- Modify `src/tcalc/ui/widgets/common/types.py`, `src/tcalc/ui/widgets/keypad/custom_pad.py`.
- Create `tests/py/unit/ui/test_typed_tables.py` (new module, new file), `tests/py/unit/ui/test_theme_overrides.py` (theme loading has no test file yet; `test_theme_colors.py` is about the palette), `tests/py/ui/test_custom_pad_layout.py` (no custom pad test file exists).

### Task 1: The converter

**Files:** Create `src/tcalc/typed_tables.py`, `tests/py/unit/ui/test_typed_tables.py`.

**Interfaces:**
- Produces: `class TableError(Exception)`; `build(cls: type[T], table: object, where: str) -> T`; `override(obj: T, table: object, where: str) -> T` (T a dataclass type). Logger `logging.getLogger("tcalc.typed_tables")`, warnings only.
- Field types supported, read with `typing.get_type_hints`: `int` (not `bool`), `float` (an `int` accepted), `str`, `bool`, `Path` (from `str`), an `Enum` subclass (by value, then by member name), `tuple[X, ...]` (from a list), a nested dataclass (from a table).
- Messages: `"{where}.{key}: missing"`, `"{where}.{key}: unknown key"`, `"{where}.{key}: expected int, got str"`, `"{where}: expected a table, got list"`.

- [ ] **Step 1: Write the failing tests.** Small test dataclasses in the test file (`Inner(n: int)`, `Outer(i: int, f: float, s: str, b: bool, e: Fit, t: tuple[str, ...], inner: Inner, opt: str = "x")` with `Fit(Enum)` of `CONTAIN = "contain"`). One parametrized `test_build` over rows `(table, expected_or_error)`, ids: `all fields`, `int for float`, `enum by value`, `enum by name`, `default used`, `missing key`, `unknown key`, `wrong type`, `bool for int`, `not a table`, `nested wrong type` (message `outer.inner.n: expected int, got str`). One parametrized `test_override` over `(table, expected_fields, logged)`, ids: `applies`, `unknown key skipped`, `wrong type skipped`, `not a table skipped`; it asserts the result with `dataclasses.asdict` and the warning text with `caplog`.
- [ ] **Step 2: Run** `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_typed_tables.py -q`. Expected: collection error, `No module named 'tcalc.typed_tables'`.
- [ ] **Step 3: Implement** `build` and `override` sharing one private `_convert(value, hint, where) -> object` step. `override` builds the changed fields with `_convert`, skips and logs each bad key, and returns `dataclasses.replace(obj, **changed)`.
- [ ] **Step 4: Run** the same command. Expected: all pass. `make typecheck`: no issues.
- [ ] **Step 5: Commit** (human agent approval): `refactor/config: add a converter from tables to dataclasses`.

### Task 2: Typed `config.toml`

**Files:** Modify `src/tcalc/ui/config.py`; Test: `tests/py/unit/ui/test_typed_tables.py`.

**Interfaces:**
- Consumes: `build` (Task 1).
- Produces: one frozen, slotted dataclass per table, named after it (`WindowConfig`, `ColorUsage`, `FontsConfig`, `StyleConfig`, `OptionGroupConfig`, `IconsConfig`, `ToastConfig`, `SidePanelConfig`, `HistoryConfig` with `style: HistoryStyleConfig`, `math: HistoryMathConfig`, `MemoryConfig` with `style`, `KeypadConfig` with `custom: CustomPadConfig`, `CalcConfig` with `layout`, `style`, `display: DisplayConfig` with `result: ResultConfig`, `topbar`, `ManubarConfig` with `style`, `preset`), root `UiConfig`; `CONFIG: UiConfig = build(UiConfig, tomllib.load(...), "config")`; `StyleTable(path: tuple[str, ...], prefix: str)` and `STYLESHEET_TABLES: tuple[StyleTable, ...]` with the eight rows the spec lists, in its order. `scroll_anim_curve: QEasingCurve.Type`; `icons.untinted: tuple[str, ...]`.
- In this task the old dict exports stay beside `CONFIG`, so the readers keep working; Task 5 deletes them. Ruling: two copies for the length of the branch, never merged.

- [ ] **Step 1: Write the failing test** `test_config_toml_builds`: `build(UiConfig, tomllib.load(<config.toml>), "config") == CONFIG`, and three parametrized rows on a deep copy of the loaded dict (`missing key`: delete `calc.display.result.btn_size`; `unknown key`: add `window.extra = 1`; `wrong type`: `toast.pad_y = "6"`), each `pytest.raises(TableError, match=...)` with the dotted key.
- [ ] **Step 2: Run** the file. Expected: ImportError on `UiConfig`.
- [ ] **Step 3: Implement** the dataclasses and `CONFIG`. No table move yet.
- [ ] **Step 4: Run** the file and `make typecheck`. Expected: pass.
- [ ] **Step 5: Commit** (human agent approval): `refactor/config: load config.toml into typed tables`.

### Task 3: Typed theme overrides (fixes #105)

**Files:** Modify `src/tcalc/theme.py`, `src/tcalc/ui/styles.py`, `src/tcalc/ui/config.toml`, `src/tcalc/ui/config.py`, `src/tcalc/themes/light.toml`, `dark.toml`, `src/tcalc/ui/manubar/style.qss`, `src/tcalc/ui/widgets/keypad/style.qss`, `src/tcalc/ui/widgets/utils.py`, `src/tcalc/ui/widgets/math/math_primitives.py`, every `app_fonts()` caller; Test: create `tests/py/unit/ui/test_theme_overrides.py`, modify `tests/py/unit/ui/test_styles.py`, `tests/py/unit/ui/test_theme_colors.py`, `tests/py/unit/ui/test_picture_layer.py`.

**Interfaces:**
- Consumes: `build`, `override`, `CONFIG`, `STYLESHEET_TABLES`, `FontsConfig`, `ColorUsage`.
- Produces on `Theme`: `ui: UiConfig`, `fonts: FontsConfig`, `colors: dict[str, str]` (stays a mapping), `color(name: str) -> str`, `qcolor(name: str) -> QColor` (a color name now, not a place). `Theme.color_usage` and `Theme.spacing` go; `ui.color_usage` replaces the first. `styles.AppFonts` and `styles.app_fonts()` go; callers read `get_theme().fonts` with the renamed fields (`family_default`, `size_default`, `family_monospace`).
- Log `where` strings: `"theme <variant> [spacing]"`, `"theme <variant> [fonts]"`, `"theme <variant> [color_usage]"`, `"theme <variant> [colors]"`, `"theme <variant> [[pictures]] #<n>"`.

- [ ] **Step 1: Move the values** (spec "config.toml moves"): the five radii and `button_padding` and `icon_padding = 4` into `[style]`; `keypad_min_pt`, `keypad_max_pt`, `menu_size`, `picker_size = 9` into `[fonts]` (out of `[keypad]` and `[manubar.style]`); `light.toml` and `dark.toml` keep `name` and `[colors]` only. Update the dataclasses of Task 2 to match.
- [ ] **Step 2: Write the failing tests** in `test_theme_overrides.py`, each writing a theme into the `_user_themes` folder (see `tests/py/unit/ui/conftest.py`):
  - `test_broken_part_falls_back`, parametrized over the #105 rows, ids `spacing array`, `spacing wrong type`, `spacing unknown name`, `fonts array`, `fonts wrong type`, `colors array`, `color value not text`, `color_usage array`, `color_usage missing color`, `pictures not an array`, `picture bad fit`, `picture tint missing`. Each: `custom_themes()` lists it, `load_theme(name)` returns, the broken value equals the Dark or `CONFIG` value, a sibling good value in the same file applies, `caplog` holds the theme name, the table and the key; then `load_theme("dark")` and the `ui` equals `CONFIG`.
  - `test_spacing_override_reaches_stylesheet_and_python`: a theme with `[spacing] frac_toggle_radius = 40` and `key_radius = 7`: `get_theme().ui.calc.display.result.frac_toggle_radius == 40`, `get_theme().ui.style.key_radius == 7`, and `"border-radius: 40px"` in `_build_stylesheet()`.
  - `test_bundled_themes_style_unchanged`: for `light`, `dark`, `kitty`, `retro`, `sponge`, the SHA-256 of `_build_stylesheet()` equals a value pinned in the test from master `a88c553` (record it there once, from a detached checkout; the pin carries that commit and the date). The substituted text does not change when QSS variables are renamed, so it holds across the task.
  - `test_stylesheet_names_are_unique`: every name the `STYLESHEET_TABLES` rows and the `FontsConfig` int fields produce occurs once.
  - `test_builtin_themes_have_every_color_usage_color` (into `test_theme_colors.py` as a parametrized row over `light`, `dark` if a test there already walks variants): every `ColorUsage` value is a key of that theme's colors.
- [ ] **Step 3: Run** `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_theme_overrides.py -q`. Expected: failures (the old `Theme` raises `TypeError` on the array rows, has no `ui`).
- [ ] **Step 4: Implement in `theme.py`.** `ui`: group the theme's `[spacing]` names by the `STYLESHEET_TABLES` row that owns them (name = prefix + field), `override` each row's table, put it back with `dataclasses.replace` along its path; an unowned name is logged and skipped. `fonts = override(CONFIG.fonts, data["fonts"] ...)`. `color_usage = override(CONFIG.color_usage, ...)`, then each place whose color is missing from `colors` is logged and set back to `CONFIG.color_usage`'s value. `colors`: base colors, then the theme's string values (others logged). Pictures: `build(ThemePicture, entry, where)`, then `replace(p, file=folder / p.file)`; a bad entry or a tint not in `colors` is logged and skipped. `ThemePicture.from_config` goes. A table of the wrong shape never reaches `{**...}`.
- [ ] **Step 5: Implement in `styles.py`.** `_build_subs` is one comprehension over the colors, the `ui.color_usage` places (`theme.color(value)`), the `STYLESHEET_TABLES` int fields with their prefix, and the `fonts` int fields; no key string, one `str(value)`. `_build_palette` passes `theme.ui.color_usage.<place>` attributes. QSS: `$menu_font_size` to `$menu_size`, `$picker_font_size` to `$picker_size`. `ui/widgets/utils.py` reads `get_theme().ui.style.key_radius` (no `int()`); `math_primitives.py` passes its place as an attribute.
- [ ] **Step 6: Rewrite the tests that patched dicts** (`test_styles.py` menu, picker, color place and spacing tests; `test_config_defaults` in `test_picture_layer.py`) to write a user theme instead; their assertions stay.
- [ ] **Step 7: Run** `PYTHONPATH=src python -m pytest tests/py/unit/ui -q` and `make typecheck`. Expected: pass.
- [ ] **Step 8: Commit** (human agent approval): `refactor/theme: resolve theme overrides into typed tables and skip only a broken part`.

### Task 4: Every read uses `CONFIG`

**Files:** Modify `src/tcalc/ui/config.py` and every remaining importer of its old names (`ui/utils.py`, `ui/widgets/history/{storage,style,history}.py`, `ui/window.py`, `ui/manubar/menus/view.py`, `ui/widgets/side_panel/side_panel.py`, `ui/widgets/memory/memory.py`, `ui/widgets/keypad/{keypad,widgets,custom_pad}.py`, `ui/widgets/common/button.py`, `ui/widgets/calc/__init__.py`, `ui/widgets/calc/topbar/topbar.py`, `ui/widgets/calc/display/display.py`, `ui/widgets/calc/display/result/result.py`, `ui/widgets/calc/display/expression/expression.py`), `tests/py/ui/test_history.py`, `tests/py/ui/test_result_widget.py`, `tests/py/unit/ui/test_styles.py`.

**Interfaces:** Consumes `CONFIG`. Removes the 17 dict exports, `_config`, `get_history_width_from_total`.

- [ ] **Step 1: Replace** each dict read with the `CONFIG` attribute, drop its `int()`/`float()`/`str()` and `.get` fallback (`side_panel.py`'s 45 and `result.py`'s 30 go; the config's 30 stays). A module that took a table under an alias (`history_style as style`) binds `style = CONFIG.history.style`.
- [ ] **Step 2: Run** `make typecheck`. Expected: no issues; an attribute typo is now a mypy error.
- [ ] **Step 3: Verify** none is left: `grep -rnE "_config\b|_style\b|\[\"[a-z_]+\"\]" src/tcalc --include='*.py'` shows no config read (the custom pad's saved-data reads remain until Task 6; list them in the report).
- [ ] **Step 4: Run** `make py-test`. Expected: exit 0.
- [ ] **Step 5: Commit** (human agent approval): `refactor/config: read every config value as a typed attribute`.

### Task 5: Stylesheet-table reads go through the theme

**Files:** Modify `src/tcalc/ui/widgets/calc/topbar/topbar.py`, `src/tcalc/ui/widgets/calc/display/display.py`, `src/tcalc/ui/widgets/calc/display/result/result.py`, `src/tcalc/ui/widgets/calc/display/expression/expression.py`, `src/tcalc/ui/widgets/calc/__init__.py`; Test: `tests/py/unit/ui/test_theme_overrides.py`.

**Interfaces:** Consumes `Theme.ui`, `STYLESHEET_TABLES`.

- [ ] **Step 1: Write the failing test** `test_no_stylesheet_table_read_through_config`: in every `src/tcalc/**/*.py` except `theme.py`, no `CONFIG.` followed by the dotted path of a `STYLESHEET_TABLES` row (`CONFIG.calc.topbar`, `CONFIG.style`...). The message names file and line.
- [ ] **Step 2: Run** it. Expected: FAIL listing the `CONFIG` reads Task 4 left in the five modules.
- [ ] **Step 3: Implement.** Each widget takes its table once where it builds (`cfg = get_theme().ui.calc.topbar`) and reads attributes.
- [ ] **Step 4: Run** `PYTHONPATH=src python -m pytest tests/py/ui/test_result_widget.py -q`, the overrides file and `make typecheck`. Expected: pass.
- [ ] **Step 5: Commit** (human agent approval): `refactor/calc: read the stylesheet tables through the theme`.

### Task 6: Typed custom pad layout

**Files:** Modify `src/tcalc/ui/widgets/common/types.py`, `src/tcalc/ui/widgets/keypad/custom_pad.py`; Test: create `tests/py/ui/test_custom_pad_layout.py`.

**Interfaces:**
- Consumes: `build`, `TableError`.
- Produces in `types.py`: `KeySettings` as a frozen dataclass (`operation: str = ""`, `bg_color: str = ""`, `text_color: str = ""`); `GridLayout(max_rows: int, keys: tuple[KeySettings, ...])`; `PadLayout(label: str, cols: int, rows: int, grids: tuple[GridLayout, ...])`. `KeyDef.to_settings() -> KeySettings`.
- Kept from today's `_load`, each one a user path: a pad with no saved layout (every pad the GUI creates) starts from the `[keypad.custom]` defaults and logs nothing; a key whose `operation` is empty or no longer names an operation or constant is skipped, and its index still counts for the next keys' row and column; grids past `rows * cols` are dropped and missing ones get `default_max_rows`. `_save` always writes `label`, `cols`, `rows` and `grids` with `max_rows` and `keys`, so those are required. A layout saved by an earlier version is not required to load.

- [ ] **Step 1: Write the failing tests:** `test_edited_layout_round_trips`, parametrized over one edit per row through the pad's own edit methods, ids `operation added`, `operation replaced`, `theme color`, `custom color`, `key removed`, `cols changed`, `rows changed`, `grid rows changed`, `renamed`; each saves (`_toggle_edit(False)` or the method's own save) and a new pad with the same id has the same label, cols, rows, grid `max_rows`, keys (operation, row, col) and colors; `test_new_pad_starts_from_defaults_silently` (no saved layout: `CONFIG.keypad.custom` defaults, `caplog` empty); `test_unknown_operation_is_skipped_and_keeps_positions` (keys `SIN`, `NO_SUCH_OP`, `COS` in a grid of `max_rows` 2: two keys load, `COS` at row 0, column 1); `test_extra_grids_are_dropped_and_missing_ones_added` (rows: 3 saved grids for a 1x2 pad gives 2; 1 saved grid for a 1x2 pad gives 2, the second with `default_max_rows`); `test_layout_of_the_wrong_shape_starts_from_defaults` (rows: `grids` a dict, `cols` a string; the pad has `CONFIG.keypad.custom` defaults and `caplog` names the pad and the key). Isolate `QSettings` in a temporary INI file (`docs/rules/ai/tests.md`). The keep-today tests pass before the change too; they guard it, and the red of this task comes from the import of `PadLayout`.
- [ ] **Step 2: Run** the file. Expected: FAIL on the import of `PadLayout`.
- [ ] **Step 3: Implement.** `_load` returns at once when nothing is saved, then reads `build(PadLayout, json.loads(raw), f"custom pad {id}")`; a `TableError` or JSON error is logged and the pad keeps its defaults. `_save` writes `json.dumps(dataclasses.asdict(layout))`. `_load_keys` takes `tuple[KeySettings, ...]` and keeps its skip and position rules. The edit paths (`_replace_operation`, `_set_key_color`, `_remove_key`, `_sync_grid_count`, `_rename_pad`, `_confirm_remove_pad`) work on `KeyDef` and change only where they read `CONFIG`.
- [ ] **Step 4: Run** the file, `tests/py/unit/ui/test_styles.py`, `tests/py/ui/test_theme_switch.py` (one process each) and `make typecheck`. Expected: pass.
- [ ] **Step 5: Commit** (human agent approval): `refactor/keypad: read the custom pad layout into typed tables`.

### Task 7: Docs and the final check

**Files:** Modify `src/tcalc/themes/theme-template.toml`, `docs/superpowers/findings/typed-config.md`.

- [ ] **Step 1:** `theme-template.toml`: the radii and font defaults now live in `config.toml` `[style]` and `[fonts]`; `[spacing]` overrides any number of the stylesheet tables by name.
- [ ] **Step 2:** Findings: replace the "how values flow today" entry with how they flow now, dated.
- [ ] **Step 3: Verify** the spec's acceptance: the grep of Task 4 Step 3 (no hits now), `make typecheck`, `make py-test`. Put the commands and outputs in the report.
- [ ] **Step 4: Hand over** to the human agent to run the app and switch every bundled theme, light and dark, flat and math mode.
- [ ] **Step 5: Commit** (human agent approval): `docs/theme: say where theme defaults live`.
