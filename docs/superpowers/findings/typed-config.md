# Typed config (#104)

## 2026-11-02, refactor/typed-config: how config and theme values reach the code

- `config.toml` is built once into `CONFIG: UiConfig` (`src/tcalc/ui/config.py`), one frozen dataclass per table, by `typed_tables.build`; a missing, unknown or wrongly typed key stops the import with the table and key in the message.
- `light.toml` and `dark.toml` hold `name` and `[colors]` only. The corner radii, `button_padding` and `icon_padding` live in `[style]`; the font values (`keypad_min_pt`, `keypad_max_pt`, `menu_size`, `picker_size`) in `[fonts]`.
- `Theme(variant)` resolves once: `colors` (base, then the theme's), and `ui`, which is `CONFIG` with the theme's `[fonts]`, `[color_usage]` and `[spacing]` applied. A broken part is logged (`theme <variant> [table].key: why`) and skipped; only an unparsable file, a missing `name` or a bad `base` rejects the theme.
- A `[spacing]` name is a `STYLESHEET_TABLES` row's prefix plus an int field; `_build_subs` builds the `$name` substitutions from the same rows and `ui.fonts`, so the stylesheet and `get_theme().ui` see the same value. No name occurs twice (`test_stylesheet_names_are_unique`).
- Python reads a stylesheet table through `get_theme().ui` (top bar, display, result, expression fonts, `key_radius`), everything else through `CONFIG`; `test_no_stylesheet_table_read_through_config` keeps it so. A widget built under one theme keeps its Python-read values until it is rebuilt; the stylesheet follows every switch.
- A `[color_usage]` place is an attribute; a caller that re-resolves on every switch (icons, symbol icons) passes a `ColorPlace` selector (`lambda u: u.icon_color`).

## 2026-11-02: picker_size followed the theme's size_default, not 9

The spec moved `picker_size = 9` into `[fonts]` on the claim that the code's fallback was 9. The fallback was `fonts.get("picker_size", fonts["size_default"])` after the theme's `[fonts]` merge, so Kitty (14) and Retro (18) drew the picker at their own `size_default`. The stylesheet hash pin in `tests/py/unit/ui/test_theme_overrides.py` caught it (`font-size: 14pt` became `9pt`). Kitty and Retro now set `picker_size` themselves; `theme-template.toml` no longer says it defaults to `size_default`.
