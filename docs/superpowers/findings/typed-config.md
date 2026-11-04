# Typed config (#104)

## 2026-11-02, refactor/typed-config: how config and theme values reach the code

- `config.toml` (behavior values) and `look.toml` (the look) are each built once, `CONFIG: UiConfig` in `src/tcalc/ui/config.py` and `DEFAULT_LOOK: Look` in `src/tcalc/ui/look.py`, one frozen dataclass per table, by `typed_tables.build`; a missing, unknown or wrongly typed key stops the import with the table and key in the message.
- `look.toml` has one table per UI area (`[fonts]`, `[palette]`, `[keypad]`, `[menu]`...). A field named `color` or ending in `_color` holds a color name from the theme's `[colors]`, never a color; the other fields are sizes, radii and paddings.
- `light.toml` and `dark.toml` hold `name` and `[colors]` only. A theme file is a partial `look.toml`: `Theme(variant)` resolves `colors` (base, then the theme's) and `Theme.look = override(DEFAULT_LOOK, ...)` with the theme's area tables applied. A broken part is logged (`theme <variant> [table].key: why`) and skipped; only an unparsable file, a missing `name` or a bad `base` rejects the theme.
- Stylesheets substitute `$<area>_<field>` (`src/tcalc/ui/styles.py`), built from `Theme.look`, so the stylesheet and Python code read the same value; a color field is resolved through `Theme.colors` first.
- Python reads the look through `get_theme().look`, behavior values through `CONFIG`. A widget built under one theme keeps its Python-read values until it is rebuilt; the stylesheet follows every switch.

## 2026-11-02: picker_size followed the theme's size_default, not 9

The spec moved `picker_size = 9` into `[fonts]` on the claim that the code's fallback was 9. The fallback was `fonts.get("picker_size", fonts["size_default"])` after the theme's `[fonts]` merge, so Kitty (14) and Retro (18) drew the picker at their own `size_default`. The stylesheet hash pin in `tests/py/unit/ui/test_theme_overrides.py` caught it (`font-size: 14pt` became `9pt`). Kitty and Retro now set `picker_size` themselves; `theme-template.toml` no longer says it defaults to `size_default`.

## 2026-11-04, master f816fac: config keys nothing reads

`grep -rn "\b<key>\b" src/tcalc tests`, leaving out `config.py` and `config.toml`, finds no read of `[history.style] result_min_pt`, `result_max_pt`, `wrap_padding_factor`, `item_padding` or `[history.math] scale_main`, `scale_aux`, `scale_script`. A history item's result has no font size of its own in config.
