# Theme areas

Issue #197 (part of #98), milestone First release (#22). How config and theme values flow today: [typed-config.md](../findings/typed-config.md).

## Why

A theme sets a value through one of two flat pools: `[spacing]` for an int of a stylesheet table, `[color_usage]` for a color place. A theme writer who wants to change the history looks for a history section and finds none: its colors are `history_*` lines in `[color_usage]`, its sizes are in `[history.style]` and `[history.math]`, which no theme can reach. The same holds for memory, and the dock titles, the dock tabs and the option groups have no setting at all. In the code every overridable name goes through a mapping (`STYLESHEET_TABLES`, `StyleTable` prefixes, `Theme._spacing`, `ColorUsage`) because the config's tables and the theme's names do not line up.

## Goals

- A theme has one table per UI area, and everything a theme can change about an area (colors, font sizes, radii, paddings) is in that table, e.g. `[history] result_color = "accent_text"`.
- The defaults are written in the same tables under the same names, so a theme table lays over the default table of the same name through the existing `override`, with no mapping code.
- What a theme must not change (layout geometry, limits, timings, icon names, and values kept fixed on purpose such as the custom pad spin box font from #106) is out of a theme's reach by structure.
- New settings: the history (expression, result, item buttons, mode buttons, Clear History) and memory font sizes and colors, the dock title font size and color, the dock tab bar (colors, radius, font size) and the option group font size.
- A theme switch applies the new settings at once, with no restart.
- The code that exists only to map flat names (listed under Removed) is deleted, not left beside the new structure.

## Non-goals

- Per keypad role hover, checked and disabled colors (#198), the template note on custom color names (#199), the settings panel format (#200).
- Changing any value.
- Making the values Python reads today follow a theme switch; they keep being read when their widget is built, as the typed config spec decided.
- Loading a custom theme written in the old format. Custom themes are not released; the bundled ones are converted in the same change, and an old `[spacing]` or `[color_usage]` table is logged as an unknown key and skipped.

## Anti-goals

- A second name for a value, or code that maps a theme name to a config name.
- A theme that can reach a behavior value.
- A bundled theme that looks different after the restructure.

## Design

**Two files, one rule.** A value goes into `src/tcalc/ui/look.toml` (new) when it is a color, a font size, a radius or a padding inside a widget's box; everything else (margins and spacing between widgets, stretch, widget heights and button sizes, limits, timings, scale factors, icon names) stays in `src/tcalc/ui/config.toml`. A theme file is a partial `look.toml`: a value is themable exactly when it is in `look.toml`. This drops theme access to the layout ints of `[calc.display]`, `[calc.display.result]` and `[calc.topbar]` and to `scroll_anim_duration`, which `[spacing]` reaches today; no bundled theme sets them.

**Types (new module).** `src/tcalc/ui/look.py` declares one `@dataclass(frozen=True, slots=True)` per area table under a root `Look`, and loads `look.toml` into the default look with `typed_tables.build`. It is a new module because its job differs from `config.py`'s: `config.py` is what no theme touches, `look.py` is what every theme lays over; `config.py` loses about as many lines as `look.py` gets. `ColorPlace` moves here as `Callable[[Look], str]`, so a tint selector reads `lambda look: look.result.frac_icon_color`.

**Partial area tables.** `typed_tables.override` builds a nested dataclass from a sub-table with `build`, which requires every field, so a theme that sets one key of an area would be rejected today. `override` is extended to override a nested dataclass field with the sub-table instead (recursively); `build` stays strict. `Theme(variant)` then makes its look in one call: `override(default_look, <the theme's tables except name, base, colors and pictures>, where)`. An unknown table or key, a behavior table such as `[keypad.custom]`, and the old `[spacing]` and `[color_usage]` all take the existing "unknown key" log.

**Colors.** A look field is a color place when its name is `color` or ends in `_color`; its value is a color name of the theme. Today's `[color_usage]` places all end in `_color`, and `[icons] color` and `[icon_button] color` are the two places that drop their area; no other field matches. After the override, a place naming a color the theme lacks is logged and takes the default look's choice: the check `Theme._color_usage` does today, run over every area. A test keeps every color place a `str`, and checks that every place of the default look names a color of `light.toml` and `dark.toml` (`test_builtin_themes_have_every_color_usage_color` today).

**Stylesheet names.** Every look field is substituted as `$<area>_<field>`: a color place as the theme's color value, any other field as its text. Most color places keep today's QSS name (`menu_text_color` is `[menu] text_color`); numbers are renamed in the QSS files (`$key_radius` becomes `$keypad_radius`). `test_stylesheet_names_are_unique` checks these names. The theme's raw color names are no longer substituted: no QSS file uses one.

**Python reads.** A widget reads a look value through `get_theme().look.<area>`. `CONFIG` holds no look table, so a read through it cannot reach one. A new setting that Python applies (a font size range, an icon size) is applied again on `theme_events.applied`, the signal `history._apply_theme_font` already uses. A widget whose look its caller chooses (an `OptionGroup` in the history versus the top bar) is passed the look's table by the caller.

## The areas

Today's values by area; the new field name drops the area (`[color_usage] history_row_color` is `[history] row_color`). Field names not given here are the plan's, for the owner to read.

- `[fonts]` (app wide): `family_default`, `size_default`, `family_monospace`.
- `[palette]`: the eight `palette_*` places.
- `[icons]`: `icon_color` as `color`. `untinted` stays in `config.toml`.
- `[display]`: `display_background_color`, the four `expression_*` places, `radical_line_color`, `radical_symbol_color`, `status_text_color`, `status_error_text_color`; from `[calc.display]` `divider_height`, `root_border_width`, `expression_font_size`, `expr_max_pt`.
- `[result]`: `result_text_color`, the three `fraction_button_*` places, `fraction_icon_color`; from `[calc.display.result]` `font_size`, `max_pt`, `btn_padding`, `frac_toggle_radius`.
- `[memory]`: the six `memory_button_*` places; `[calc.topbar]` `memory_pad_y`, `memory_pad_x`. In the history PR: `[memory.style]` `font_size`, `max_pt`.
- `[keypad]`: the 22 role key places, `key_hover_border_color`, `key_checked_color`, `key_disabled_color`, `key_disabled_text_color`, `key_symbol_color`; `[style]` `key_radius` and `button_padding`; `[calc.style]` `compact_pad_y`, `compact_pad_x`; `[fonts]` `keypad_min_pt`, `keypad_max_pt`.
- `[custom_pad]`: `add_key_color`, `add_key_hover_color`, the three `spinbox_*` places, `pad_toolbar_separator_color`, the five `pad_menu_*` places.
- `[picker]`: the five `picker_*` places; `[fonts]` `picker_size` as `font_size`.
- `[menu]`: the eight `menu_*` places, `constants_menu_symbol_color`; all of `[manubar.style]`; `[fonts]` `menu_size` as `font_size`.
- `[history]`: the six `history_*` places. In the history PR: `[history.style]` `font_size`, `max_pt`, `expr_min_pt`, `expr_max_pt`, `clr_btn_min_pt`, `clr_btn_max_pt`, `action_btn_size`; `[history.math]` `base_font`; and the new settings.
- `[options]`: the four `option_*` places; `[style]` `option_radius`; `[style.option_group]` `padding_y`, `padding_x`.
- `[icon_button]`: the six `icon_button_*` places; `[style]` `icon_button_radius`, `icon_padding`.
- `[tooltip]`: the three `tooltip_*` places; `[style]` `tooltip_radius`, `tooltip_padding`.
- `[toast]`: the four `toast_*` places; all of `[toast]`.
- `[dock]`, `[tabs]`: new, in the last PR.

**New settings.** `[history]`: expression and result font size ranges and colors (the result gets a range of its own; today it takes the list's font), item button size and color, mode button font size and colors, Clear History colors next to its existing range. `[dock]`: title font size and color, read by `DockTitleBar`. `[tabs]`: background, text, selected and hover colors, radius and font size of the tab bar of tabified docks, a new `QTabBar` rule in the window's QSS. `[options]`: font size. Each default is what the widget shows today (a size that comes from the app font is written out as `size_default`'s value), so no bundled theme changes unless it sets one.

## Removed

- `config.py`: `ColorUsage`, `FontsConfig`, `StyleConfig`, `OptionGroupConfig`, `ToastConfig`, `CalcStyleConfig`, `ManubarStyleConfig`, the look fields of `DisplayConfig`, `ResultConfig` and `TopbarConfig`, `StyleTable`, `int_fields`, `STYLESHEET_TABLES`, and `UiConfig`'s fields for them.
- `config.toml`: `[color_usage]`, `[fonts]`, `[style]`, `[style.option_group]`, `[toast]`, `[calc.style]`, `[manubar.style]`, and the moved fields of the other tables.
- `theme.py`: `Theme.ui`, `_spacing`, `_replaced`, `_color_usage` (its check runs over the look).
- `styles.py`: the table and prefix walk in `_build_subs` and the raw color substitution.
- Tests: `test_no_stylesheet_table_read_through_config`, the `[spacing]` cases of `test_theme_overrides.py` (rewritten for area tables).
- Config keys no code reads (findings, 2026-11-04): `[history.style]` `result_min_pt`, `result_max_pt`, `wrap_padding_factor`, `item_padding`; `[history.math]` `scale_main`, `scale_aux`, `scale_script`.

## Typed names (added during Part 1, owner's decision)

The converter in `typed_tables.py` types its hints and values instead of `Any`, and no value falls back to a bare `str`: a color place is a `ColorName`, an icon an `IconName`, a font family a `FontFamily` (each a `NewType`), and a color place is found by its type instead of its name. Fields with the same shape are one nested dataclass: the seven keypad roles are `[keypad.<role>]` tables of one `KeyRoleLook`, with the stylesheet name joined by `_` so no QSS changes. The Qt properties a QSS selector reads (`uiRole`, `keypadRole`, ...) and their values are named once in Python as enums, and a test fails when a QSS selector names one that Python does not define. Qt properties used only as Python state (`keyRadius`, `_expr_connected`, `_aw_scheduled`) become typed attributes, and the QSS rules no code can reach (`[presetRow]`, `[active]` in the menu bar) go.

## Themes and template

`kitty`, `retro` and `sponge` move their `[fonts]`, `[spacing]` and `[color_usage]` values into the area tables (`[keypad] radius`, `[result] frac_toggle_radius`, `[picker] text_color`...). `light.toml` and `dark.toml` stay palettes. `theme-template.toml` lists the area tables with their fields as comments and points to `look.toml` for the defaults.

## Verification

- The restructure PR leaves each bundled theme's built stylesheet byte for byte the same: the hash pins in `test_theme_overrides.py` do not change. The later PRs change a pin only after a diff of the built stylesheets shows nothing but their added rules; the diff goes in the PR.
- A theme that sets one key of an area changes that key and keeps the rest of the area.
- A theme table naming a behavior value (`[keypad.custom] spin_font_size`) has no effect and is logged.
- A test per new setting that a theme value reaches the widget and follows a switch between two themes.
- Run the app with each bundled theme and look at the history, the docks and the tabs.

## Delivery

Three PRs, in order: the restructure (two files, `look.py`, area tables, stylesheet names, themes converted, Removed; no new setting), then history and memory, then docks, tabs and options.
