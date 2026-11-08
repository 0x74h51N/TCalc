# Theme areas

Issue #197 (part of #98), milestone First release (#22). How config and theme values flow today: [typed-config.md](../findings/typed-config.md).

## Why

A theme sets a value through one of two flat pools: `[spacing]` for an int of a stylesheet table, `[color_usage]` for a color place. A theme writer who wants to change the history looks for a history section and finds none: its colors are `history_*` lines in `[color_usage]`, its sizes are in `[history.style]` and `[history.math]`, which no theme can reach. The same holds for memory, and the dock titles, the dock tabs and the option groups have no setting at all. In the code every overridable name goes through a mapping (`STYLESHEET_TABLES`, `StyleTable` prefixes, `Theme._spacing`, `ColorUsage`) because the config's tables and the theme's names do not line up.

## Goals

- A theme has one table per UI area, and everything a theme can change about an area (colors, font sizes, radii, paddings) is in that table, e.g. `[history] result_color = "accent_text"`.
- The defaults are written in the same tables under the same names, so a theme table lays over the default table of the same name through the existing `override`, with no mapping code.
- What a theme must not change (layout geometry, limits, timings, icon names, and values kept fixed on purpose such as the custom pad spin box font from #106) is out of a theme's reach by structure.
- New settings: the history (expression, result, item buttons, mode buttons, Clear History) and memory font sizes and colors, the dock title font size and color, the dock tab bar (text color, font size) and the option group font size.
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

**Colors.** A look field is a color place when its name is `color` or ends in `_color`; its value is a color name of the theme. Today's `[color_usage]` places all end in `_color`, and `[icons] color` is the one place that drops its area (Part 1 also had `[icon_button] color`, which Part 2 removes); no other field matches. After the override, a place naming a color the theme lacks is logged and takes the default look's choice: the check `Theme._color_usage` does today, run over every area. A test keeps every color place a `str`, and checks that every place of the default look names a color of `light.toml` and `dark.toml` (`test_builtin_themes_have_every_color_usage_color` today).

**Stylesheet names.** Every look field is substituted as `$<area>_<field>`: a color place as the theme's color value, any other field as its text. Most color places keep today's QSS name (`menu_text_color` is `[menu] text_color`); numbers are renamed in the QSS files (`$key_radius` becomes `$keypad_radius`). `test_stylesheet_names_are_unique` checks these names. The theme's raw color names are no longer substituted: no QSS file uses one.

**Python reads.** A widget reads a look value through `get_theme().look.<area>`. `CONFIG` holds no look table, so a read through it cannot reach one. A new setting that Python applies (a font size range, an icon size) is applied again on `theme_events.applied`, the signal `history._apply_theme_font` already uses. A widget whose look depends on where it sits (an `OptionGroup` in the history versus the top bar) gets its colors from a QSS rule on its container's object name (`#historyModes`); its caller passes a picker of its table (`look.history.mode` or `look.options`) for the radius and edge Python applies.

## The areas

Today's values by area; the new field name drops the area (`[color_usage] history_row_color` is `[history] row_color`). Field names not given here are the plan's, for the human agent to read.

- `[fonts]` (app wide): `family_default`, `size_default`, `family_monospace`.
- `[palette]`: the eight `palette_*` places.
- `[icons]`: `icon_color` as `color`. `untinted` stays in `config.toml`.
- `[display]`: `display_background_color`, the four `expression_*` places, `radical_line_color`, `radical_symbol_color`, `status_text_color`, `status_error_text_color`; from `[calc.display]` `divider_height`, `root_border_width`, `expression_font_size`, `expr_max_pt`.
- `[result]`: `result_text_color`, the three `fraction_button_*` places, `fraction_icon_color`; from `[calc.display.result]` `font_size`, `max_pt`, `btn_padding`, `frac_toggle_radius`.
- `[memory]`: the six `memory_button_*` places; `[calc.topbar]` `memory_pad_y`, `memory_pad_x`. In the history part: `[memory.style]` `font_size`, `max_pt`.
- `[keypad]`: the 22 role key places, `key_hover_border_color`, `key_checked_color`, `key_disabled_color`, `key_disabled_text_color`, `key_symbol_color`; `[style]` `key_radius` and `button_padding`; `[calc.style]` `compact_pad_y`, `compact_pad_x`; `[fonts]` `keypad_min_pt`, `keypad_max_pt`.
- `[custom_pad]`: `add_key_color`, `add_key_hover_color`, the three `spinbox_*` places, `pad_toolbar_separator_color`, the five `pad_menu_*` places.
- `[picker]`: the five `picker_*` places; `[fonts]` `picker_size` as `font_size`.
- `[menu]`: the eight `menu_*` places, `constants_menu_symbol_color`; all of `[manubar.style]`; `[fonts]` `menu_size` as `font_size`.
- `[history]`: the six `history_*` places. In the history part: `[history.style]` `font_size`, `max_pt`, `expr_min_pt`, `expr_max_pt`, `clr_btn_min_pt`, `clr_btn_max_pt`, `action_btn_size`; `[history.math]` `base_font`; and the new settings.
- `[options]`: the four `option_*` places; `[style]` `option_radius`; `[style.option_group]` `padding_y`, `padding_x`.
- `[icon_button]`: the six `icon_button_*` places; `[style]` `icon_button_radius`, `icon_padding`. Part 2 removes it: the shared icon button rule reads the `[palette]` colors with a fixed radius and padding, and only the history item buttons get a table, `[history.icon_button]`.
- `[tooltip]`: the three `tooltip_*` places; `[style]` `tooltip_radius`, `tooltip_padding`.
- `[toast]`: the four `toast_*` places; all of `[toast]`.
- `[dock]`, `[tabs]`: new, in the last part.

**New settings.** `[history]`: expression and result font size ranges and colors (the result gets a range of its own; today it takes the list's font), the item buttons as a `[history.icon_button]` table (size, radius, hover and pressed colors, the raised edge's light and shadow colors, and a button and icon color each for copy and delete), the mode buttons as a `[history.mode]` table of the `[options]` shape (an `OptionsLook`, so a theme may set one key of it), Clear History colors next to its existing range. `[dock]`: title font size and color, read by `DockTitleBar`. `[tabs]`: text color and font size of the tab bar of tabified docks, a new `QTabBar::tab` rule in the window's QSS; a tab background or radius would drop the style's own tab, so the tab box goes with the edges (#203). `[options]`: font size, added with `[history.mode]` since both share the shape. Each default is what the widget shows today (a size that comes from the app font is written out as `size_default`'s value), so no bundled theme changes unless it sets one.

**Radius and raised edges (human agent's review of Part 2).** Qt squares a radius above half a button's shorter side, so Python caps every themed button radius at that half and the button is as round as it fits; `[memory]` gains `radius`. `[tooltip] radius` rounds the whole tooltip box, not only its border. `[keypad]`, `[memory]`, `[options]` and `[history.mode]` gain a raised edge: `edge_width` (0, none, by default), `edge_light_color` on the top and left, `edge_shadow_color` on the bottom and right, swapped while pressed or checked. Any QSS border drops the Fusion button frame, so the edge rules apply only under a theme whose edge width is above 0, and the default themes render as before. The edge's default colors are `button_highlight` and `button_shadow`, the same in every built-in palette, so a shadow is dark on a light theme too.

## Removed

- `config.py`: `ColorUsage`, `FontsConfig`, `StyleConfig`, `OptionGroupConfig`, `ToastConfig`, `CalcStyleConfig`, `ManubarStyleConfig`, the look fields of `DisplayConfig`, `ResultConfig` and `TopbarConfig`, `StyleTable`, `int_fields`, `STYLESHEET_TABLES`, and `UiConfig`'s fields for them.
- `config.toml`: `[color_usage]`, `[fonts]`, `[style]`, `[style.option_group]`, `[toast]`, `[calc.style]`, `[manubar.style]`, and the moved fields of the other tables.
- `theme.py`: `Theme.ui`, `_spacing`, `_replaced`, `_color_usage` (its check runs over the look).
- `styles.py`: the table and prefix walk in `_build_subs` and the raw color substitution.
- Tests: `test_no_stylesheet_table_read_through_config`, the `[spacing]` cases of `test_theme_overrides.py` (rewritten for area tables).
- Config keys no code reads (findings, 2026-11-04): `[history.style]` `result_min_pt`, `result_max_pt`, `wrap_padding_factor`, `item_padding`; `[history.math]` `scale_main`, `scale_aux`, `scale_script`.

## Typed names (added during Part 1, human agent's decision)

The converter in `typed_tables.py` types its hints and values instead of `Any`, and no value falls back to a bare `str`: a color place is a `ColorName` and a font family a `FontFamily` (each a `NewType`), and a color place is found by its type instead of its name. Icon names are the members of an `Icon` enum, and a test keeps them equal to the bundled icon files. Fields with the same shape are one nested dataclass: the seven keypad roles are `[keypad.<role>]` tables of one `KeyRoleLook`, with the stylesheet name joined by `_` so no QSS changes. The Qt properties a QSS selector reads (`uiRole`, `keypadRole`, ...) and their values are named once in Python as enums, and a test fails when a QSS selector names one that Python does not define. Qt properties used only as Python state (`keyRadius`, `_expr_connected`, `_aw_scheduled`) become typed attributes, and the QSS rules no code can reach (`[presetRow]`, `[active]` in the menu bar) go.

## Shared types (human agent's review of Part 3)

This section is the schema as it stands; the area keys above and the themes' keys in the plan's Tasks 2 to 9 are the steps on the way to it. One setting's difference does not make a dataclass, and there is no inheritance between look types. A button has one type, `Button`, wherever it stands; text is `Text` (a color and a font range), a frame is `Panel`, and `Colors`, `Edge`, `FontRange` and `Insets` are the small parts. A setting one place does not draw exists there without effect.

- `Colors`: `color: ColorName`, `text_color: ColorName`.
- `Edge`: `width: int`, `light_color: ColorName`, `shadow_color: ColorName`.
- `FontRange`: `min_pt: int`, `max_pt: int`.
- `Insets`: `y: int`, `x: int`.
- `Text`: `color: ColorName`, `font: FontRange`.
- `Button`: `color: ColorName`, `hover_color: ColorName`, `pressed_color: ColorName`, `text: Text`, `disabled: Colors`, `checked: Colors`, `radius: int`, `edge: Edge`, `padding: Insets`.
- `Panel`: `background_color: ColorName`, `text: Text`, `border_color: ColorName`, `hover_color: ColorName`, `separator_color: ColorName`, `list_background_color: ColorName`, `radius: int`, `padding: Insets`.
- `FontsLook`: `family_default: FontFamily`, `size_default: int`, `family_monospace: FontFamily`.
- `PaletteLook`: `window_color: ColorName`, `window_text_color: ColorName`, `base_color: ColorName`, `text_color: ColorName`, `button_color: ColorName`, `button_text_color: ColorName`, `highlight_color: ColorName`, `highlighted_text_color: ColorName`, `icon_color: ColorName`.
- `ExpressionLook`: `text: Text`, `selection: Colors`, `slot_focus_color: ColorName`.
- `DisplayLook`: `background_color: ColorName`, `expression: ExpressionLook`, `radical_line_color: ColorName`, `radical_symbol_color: ColorName`, `status_text_color: ColorName`, `status_error_text_color: ColorName`, `divider_height: int`, `root_border_width: int`.
- `ResultLook`: `text: Text`, `fraction: Button`.
- `KeypadLook`: `button: Button`, `number: Button`, `operator: Button`, `action: Button`, `trig: Button`, `function: Button`, `power: Button`, `hover_border_color: ColorName`, `symbol_color: ColorName`, `compact_padding: Insets`.
- `CustomPadLook`: `add_key: Button`, `spinbox: Button`, `spinbox_focus_border_color: ColorName`, `toolbar_separator_color: ColorName`, `menu: Panel`.
- `MenuLook`: `panel: Panel`, `item: Button`, `selected_border_color: ColorName`, `constants_symbol_color: ColorName`, `item_margin: int`, `item_min_width: int`, `icon_padding_left: int`, `icon_padding_right: int`, `separator_height: int`, `separator_margin: Insets`.
- `HistoryLook`: `background_color: ColorName`, `text: Text`, `row_color: ColorName`, `alternate_row_color: ColorName`, `selected: Colors`, `math_font_size: int`, `expression: Text`, `result: Text`, `icon_button_size: int`, `button: Button`, `copy: Button`, `delete: Button`, `clear: Button`, `mode: Button`.
- `ToastLook`: `text: Text`, `info_color: ColorName`, `warn_color: ColorName`, `error_color: ColorName`, `padding: Insets`, `radius: int`.
- `Look`: `fonts: FontsLook`, `palette: PaletteLook`, `display: DisplayLook`, `result: ResultLook`, `memory: Button`, `keypad: KeypadLook`, `custom_pad: CustomPadLook`, `picker: Panel`, `menu: MenuLook`, `history: HistoryLook`, `options: Button`, `tooltip: Panel`, `toast: ToastLook`, `dock: Text`, `tabs: Text`.

Where the settings live:

- `Button`: `memory`, `options`, `result.fraction`, `keypad.button` and its kinds `number`, `operator`, `action`, `trig`, `function`, `power`, `history.button` and its kinds `copy`, `delete`, `clear`, `mode`, `custom_pad.add_key`, `custom_pad.spinbox`, `menu.item` (checked is the selected item).
- `Panel`: `tooltip`, `picker`, `custom_pad.menu`, `menu.panel`.
- A fixed font size is the `min_pt` of its range: the options, `history.mode`, `Panel`, `toast`, `dock`, `tabs`.
- The icon of an icon button is its `text.color`; the single-color icons are `palette.icon_color`.

Shared buttons: `[keypad.button]` and `[history.button]` are where that area's buttons start. `with_shared_buttons` lays them under each of the area's `Button` tables before `build` and `override`, and a value in the button's own table wins, so a kind writes only what differs or all of its settings. There is no shared table across areas. A key's radius, edge, padding, font, disabled and checked are read from `keypad.button`; the copy and delete hover, pressed, radius and edge from `history.button`.

A key's hover is its own color unless a theme gives one: `transparent` and `none` would show what is behind the key (findings, `typed-config.md`). `look.toml` writes a button's parts as inline tables, at most two levels deep; a theme may use either form.

## Themes and template

`kitty`, `retro` and `sponge` move their `[fonts]`, `[spacing]` and `[color_usage]` values into the area tables (`[keypad.button] radius`, `[result.fraction] radius`, `[picker.text] color`...). `light.toml` and `dark.toml` stay palettes. `theme-template.toml` lists the area tables with their fields as comments and points to `look.toml` for the defaults. It also says how the shared buttons work.

## Verification

- The restructure leaves each bundled theme's built stylesheet byte for byte the same: the hash pins in `test_theme_overrides.py` do not change. The later parts change a pin only after a diff of the built stylesheets shows nothing but their added rules; the diff goes in the PR.
- A theme that sets one key of an area changes that key and keeps the rest of the area.
- A theme table naming a behavior value (`[keypad.custom] spin_font_size`) has no effect and is logged.
- A test per new setting that a theme value reaches the widget and follows a switch between two themes.
- Run the app with each bundled theme and look at the history, the docks and the tabs.

## Delivery

One PR (#201) in three parts, in order: the restructure (two files, `look.py`, area tables, stylesheet names, themes converted, Removed; no new setting), then history, memory and the option groups, then docks and tabs.
