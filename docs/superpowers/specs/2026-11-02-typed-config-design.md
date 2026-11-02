# Typed config tables

Issue #104, milestone First release (#22). Also fixes #105. How the values flow today: [typed-config.md](../findings/typed-config.md).

## Why

Every config value is read as `dict[str, Any]` with a string key: about 110 reads under `src/tcalc/`, many wrapped in `int(...)` or `str(...)`, some with a `.get(name, default)` fallback that is a second copy of the value (`side_panel.py` falls back to 45 ms while the config says 30). A misspelled or removed key fails only when its widget is built, and mypy cannot see it. A theme's `[spacing]` overrides config numbers by name, but only in the stylesheet: a Python read of the same value ignores the theme, and an unknown name is accepted and does nothing. A theme table of the wrong shape (`[[spacing]]`) stops the app at launch (#105). The custom pad's saved layout is read the same way, with string keys and casts.

## Goals

- Every table of `src/tcalc/ui/config.toml` is a frozen dataclass, and every read is an attribute with a known type. No string-key config read and no config cast is left under `src/tcalc/`.
- A theme's overrides go through the same types, and the stylesheet and the Python reads see the same value.
- A value a theme does not set comes from its base theme, then from `config.toml`.
- A mistake in a theme (unknown name, wrong type, table of the wrong shape) is logged with the theme, the table and the key, and only that part is skipped; the rest of the theme applies (#105).
- Theme switching stays as it is today: the stylesheet and palette change at once, with no restart.
- The custom pad's saved layout is read into typed objects, and every layout this version saves (after creating a pad and after each edit) loads back as it was. Loading a layout saved by an earlier version is not required.

## Non-goals

- New config values or theme settings, and grouping theme overrides by area (#98). A theme's `[spacing]` stays one flat namespace, as `theme-template.toml` documents it.
- Changing any value.
- QSettings keys (#181).
- Making a Python read follow a live theme switch. A value Python reads while building a widget follows the theme the widget is built under; the stylesheet keeps following every switch.

## Anti-goals

- A theme mistake that stops the app or drops the whole theme. A TOML syntax error still skips the whole theme, as #105 accepts.
- Defaults in code: a value has one home, `config.toml` (or the dataclass default of a theme field that is optional by the theme format, such as a picture's `fit`).
- A widget that branches on the theme or re-reads values on a switch to make this work.

## Design

**Types.** `src/tcalc/ui/config.py` declares one `@dataclass(frozen=True, slots=True)` per table, nested for nested tables, under one root `UiConfig`, and loads `config.toml` into `CONFIG: UiConfig` once at import. It exports the types and `CONFIG` instead of the 17 dict names. A value that takes one of a few values is an enum (`scroll_anim_curve` is a `QEasingCurve.Type`, read from its name); a list is a tuple (`icons.untinted`). This is the pattern `theme.py` and `core/ops.py` use.

**The converter (new module).** `src/tcalc/typed_tables.py` turns a TOML (or JSON) table into a dataclass by its fields. It is new because three loaders in three places need it (the config, the theme, the custom pad's saved layout) and nothing in `src/tcalc/` converts by dataclass fields today. It has one shared step and two entry points:

- `build(cls, table, where) -> cls` makes an object: a field without a value is an error unless the dataclass gives it a default, an unknown key is an error, and a value of the wrong type is an error. The error names `where` and the key (`calc.display.result.btn_size: expected int, got str`). An int is accepted for a float field; a nested dataclass is built from a sub-table; an enum is read from its value or name.
- `override(obj, table, where) -> obj` applies a partial table with `dataclasses.replace`. Each unknown key or wrongly typed value is logged (`where`, key, why) and skipped; a `table` that is not a table at all is logged and skipped whole.

**Where a read goes.** `Theme` gets `ui: UiConfig`: `CONFIG` with the theme's overrides applied, resolved once when the theme loads (`Theme(variant)`), never per read; an untouched table is the same object as in `CONFIG`. A widget reads `CONFIG.<table>.<field>` straight from `tcalc.ui.config`, with no theme in its code. Only a value a theme can override (the stylesheet tables below) is read through `get_theme().ui`, and only where Python reads one today: the top bar's margins and spacing, the display's margins, spacing and scroll animation, the result's sizes and fonts, the expression's font sizes, and `key_radius` in `ui/widgets/utils.py`. Each takes its table once where it builds (`cfg = get_theme().ui.calc.topbar`) and reads attributes from it. A stylesheet table read through `CONFIG` would silently miss the theme, so a test fails when one is read that way outside `theme.py`. `config.py` does not import the theme, so it only declares and loads; its `get_history_width_from_total` has no caller and goes.

**What a theme file holds.** `light.toml` and `dark.toml` are palettes: `name` and `[colors]` only, since every other value lives in `config.toml`. A custom `theme.toml` may also hold `base`, `[spacing]`, `[fonts]`, `[color_usage]` and `[[pictures]]`; its font files load at startup, as today.

**Which names a theme can override.** One list in `config.py` (both `theme.py` and `styles.py` read it, and `styles.py` imports the theme, not the other way round) names the tables the stylesheet substitutes and their prefix: `style`, `style.option_group` (`option_`), `manubar.style`, `calc.style`, `calc.topbar`, `calc.display`, `calc.display.result`, `toast` (`toast_`). The `$name` substitutions are built from those tables' int fields and the int fields of `fonts` (`dataclasses.fields`) in one comprehension, so `_build_subs` holds no key string and no cast; its one `str(value)` is there because a `Template` substitutes text. A theme's `[spacing]` name is resolved through the same list to one field, so the two cannot drift. No name occurs twice in that list and the `fonts` fields together today (see the findings); a test keeps it so. A `[spacing]` name outside the list is logged and skipped.

**`config.toml` moves (no value changes).**

- The five corner radii (`key_radius`, `icon_button_radius`, `tooltip_radius`, `option_radius`, `spinbox_radius`, 2 each) move from `light.toml` and `dark.toml` into `[style]`, which drop their `[spacing]`.
- `button_padding` moves from `[keypad]` to `[style]` (only the stylesheet reads it) and keeps its name.
- `icon_padding = 4`, a literal in `styles._build_subs` today, goes into `[style]`.
- The font values move into `[fonts]` under the names a theme's `[fonts]` already uses: `[keypad] min_pt` and `max_pt` become `keypad_min_pt` and `keypad_max_pt`, `[manubar.style] menu_font_size` becomes `menu_size`, and `picker_size = 9` is added (the code's fallback to `size_default`, also 9, goes).

`theme-template.toml` says where the defaults now live.

**Fonts.** With the moves above, the `[fonts]` table is the font view: its dataclass replaces `AppFonts` and the merge in `styles.app_fonts()`, and a theme's `[fonts]` is applied to it with `override` into `Theme.fonts`. Font reads go through `get_theme().fonts`. Today `menu_font_size` reaches the stylesheet twice (from `[manubar.style]`, then from the theme's fonts, which wins by order); after the move it comes from `fonts` only, and the QSS names `$menu_font_size` and `$picker_font_size` become `$menu_size` and `$picker_size`. `menu_font_size` is then no longer a `[spacing]` name; no bundled theme uses it there, and `[fonts] menu_size` is how a theme sets it.

**Colors.** `[colors]` stays a mapping, since a theme may add its own names; a value that is not a string is logged and skipped. `[color_usage]` becomes a dataclass of places whose values are color names, overridden with `override`. After a custom theme loads, a place that names a color the theme does not have is logged and takes its base theme's choice. `light.toml` and `dark.toml` have no base to fall back to, so there a missing color is a developer mistake: a test checks that every place names one of their colors. `Theme.color(name)` and `Theme.qcolor(name)` take a color name, and a caller passes the place as an attribute (`theme.qcolor(theme.ui.color_usage.palette_window_color)`). The callers that pass a place as a string today are `styles._build_palette` and `_build_subs` and one call in `ui/widgets/math/math_primitives.py`.

**Pictures.** `ThemePicture.from_config` becomes `build(ThemePicture, ...)`: the optional fields keep their dataclass defaults. A bad `[[pictures]]` entry, or one whose `tint` is not a theme color, is logged and that entry is skipped, instead of rejecting the theme.

**Whole-theme errors.** A file that does not parse, a missing `name` or a `base` that is not built in still rejects the theme with `ThemeError`, as today. Nothing else does: each table is checked to be a table before it is used, which is the #105 crash.

**Custom pad layout.** The saved JSON (`label`, `cols`, `rows`, `grids` of `max_rows` and `keys`, each key `operation` with optional `bg_color` and `text_color`) is read with `build` into `PadLayout` and `GridLayout` dataclasses next to `KeyDef` in `ui/widgets/common/types.py`; the `KeySettings` TypedDict, read today with `entry["operation"]`, becomes a frozen dataclass too. Saved layouts always hold `label`, `cols`, `rows` and `grids` (`_save` writes them all), so those are required; the key colors keep their `""` default, since `to_settings` leaves them out when empty. `_save` writes these dataclasses with `dataclasses.asdict`, so the saved fields are the dataclass fields by construction. A layout that does not build is logged and the pad starts from the `[keypad.custom]` defaults, as a JSON error does today (a wrongly typed value crashes the app today). What `_load` does today for a user stays: a pad the GUI just created has no saved layout and starts from the defaults without a log; a key whose operation no longer exists is skipped and still counts for the next keys' positions; grids past `rows * cols` are dropped and missing ones get `default_max_rows`. The settings key itself stays (#181).

## Tests

- `config.toml` builds into `UiConfig` (it does at import; the test runs `build` on it and on a copy with a missing key, an unknown key and a wrong type, each red with the table and key in the message).
- A theme override: an unknown `[spacing]` name, a wrongly typed value and a `[[spacing]]` table are each logged and skipped while the rest of the theme applies; the #105 probe cases from the issue become rows of one parametrized test.
- A `[spacing]` override reaches both the stylesheet substitution and `get_theme().ui` (Sponge's `frac_toggle_radius`).
- The stylesheet table list and the `fonts` fields have no name twice.
- No stylesheet table is read through `CONFIG` outside `theme.py`.
- Every `[color_usage]` place names a color of `light.toml` and of `dark.toml`; in a custom theme, a place naming a missing color takes the base theme's color, logged.
- A bad `[[pictures]]` entry is skipped and the other pictures load.
- A custom pad created and edited through its edit paths (operation, colors, removed key, cols, rows, grid rows, label) saves and loads back as it was; a layout of the wrong shape is logged and the pad starts from the defaults.
- The existing theme and stylesheet tests stay green.

## Acceptance

- `grep` finds no string-key config read and no config cast under `src/tcalc/` (the command and its output go in the PR).
- `make typecheck` and `make py-test` pass.
- The app is run and every bundled theme is switched to and from, light and dark, flat and math mode.
