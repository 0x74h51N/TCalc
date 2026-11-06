# Typed config (#104)

## 2026-11-02, refactor/typed-config: how config and theme values reach the code

- `config.toml` (behavior values) and `look.toml` (the look) are each built once, `CONFIG: UiConfig` in `src/tcalc/ui/config.py` and `DEFAULT_LOOK: Look` in `src/tcalc/ui/look.py`, one frozen dataclass per table, by `typed_tables.build`; a missing, unknown or wrongly typed key stops the import with the table and key in the message.
- `look.toml` has one table per UI area (`[fonts]`, `[palette]`, `[keypad]`, `[menu]`...). A field typed `ColorName` holds a color name from the theme's `[colors]`, never a color; the other fields are sizes, radii and paddings.
- `light.toml` and `dark.toml` hold `name` and `[colors]` only. A theme file is a partial `look.toml`: `Theme(variant)` resolves `colors` (base, then the theme's) and `Theme.look = override(DEFAULT_LOOK, ...)` with the theme's area tables applied. A broken part is logged (`theme <variant> [table].key: why`) and skipped; only an unparsable file, a missing `name` or a bad `base` rejects the theme.
- Stylesheets substitute each look field by its path joined with `_` (`$keypad_radius`, `$keypad_number_color` for `[keypad.number] color`; `src/tcalc/ui/styles.py`), built from `Theme.look`, so the stylesheet and Python code read the same value; a color field is resolved through `Theme.colors` first.
- Python reads the look through `get_theme().look`, behavior values through `CONFIG`. A widget built under one theme keeps its Python-read values until it is rebuilt; the stylesheet follows every switch.

## 2026-11-02: picker_size followed the theme's size_default, not 9

The spec moved `picker_size = 9` into `[fonts]` on the claim that the code's fallback was 9. The fallback was `fonts.get("picker_size", fonts["size_default"])` after the theme's `[fonts]` merge, so Kitty (14) and Retro (18) drew the picker at their own `size_default`. A stylesheet hash pin in `test_theme_overrides.py` (removed 2026-11-06) caught it (`font-size: 14pt` became `9pt`). Kitty and Retro now set `picker_size` themselves; `theme-template.toml` no longer says it defaults to `size_default`.

## 2026-11-04, master f816fac: config keys nothing reads

`grep -rn "\b<key>\b" src/tcalc tests`, leaving out `config.py` and `config.toml`, finds no read of `[history.style] result_min_pt`, `result_max_pt`, `wrap_padding_factor`, `item_padding` or `[history.math] scale_main`, `scale_aux`, `scale_script`. A history item's result has no font size of its own in config.

## 2026-11-05, refactor/theme-areas 70d19e7: writing look.toml, and a hover that does nothing

A stylesheet `background-color` of `transparent` or `none` on `:hover` does not keep the button's color: the button shows what is behind it (drawn with `State_MouseOver`, green button on blue: `#FF0000` hover `#ff0000`, `transparent` and `none` hover `#0000ff`). So a key without a hover of its own has `hover_color` equal to its `color`.

`tomllib` takes no newline inside an inline table, so `{ ... }` stays on one line:

```bash
.venv/bin/python -c "import tomllib; tomllib.loads('[a]\ntext = {\n  color = 1,\n}\n')"
```

A bad value in `[keypad.button]` is logged once per key table, because the shared table is spread before `override` checks it. The owner chose this over a separate check for a single line of log.

## 2026-11-05: ways to get a see-through color from a theme (PySide6 6.12.0, offscreen, branch `refactor/theme-areas`)

Red at 50% on a white widget, `pixelColor` of the grab; repaint is 20 `grab()` calls over 300 `QPushButton`s:

- `background-color: rgba(255,0,0,50%)`: `#ff8080`, 4.88 ms per repaint. The documented form.
- `background-color: #80FF0000`: `#ff7f7f`, 5.07 ms. Works, but the Color type in the style sheet reference lists only `#rrggbb`.
- Opaque `#FF0000`, for comparison: 5.00 ms.
- `opacity: 128` in the QSS rule: `#ff0000`, no effect. The reference says the property is "only supported for tooltips".
- `palette(button)` with an alpha `QColor` on the button's own palette: `#efefef`, the color did not arrive.
- `QGraphicsOpacityEffect` at 0.5: `#ff8080`, 11.17 ms, about 2.2 times the cost.

Blending the color over the surface into an opaque value was not probed: it cannot show a picture behind a key. No bundled theme does that (kitty's pictures target `display` and `history`), but `PictureTarget` offers the keypads, the custom pad and the window to any theme, and sponge paints a `window` picture.

## 2026-11-05: primary as the color of emphasis, seen offscreen (`refactor/theme-areas`)

Full windows of dark, light, kitty, retro and sponge, with a checked Shift, a selected history row and an open menu row: each paints `primary` on the equals key, the checked key, the checked mode button and the menu row; retro keeps gray faces and navy only on menu rows. Not seen in a real window on a desktop session. Focus borders on kitty and sponge not exercised by this pass.

The `test_history` row "mode checked text keeps its default" had passed by coincidence: it reads the palette, which never sees a `:checked` rule, and dark's `control_accent` equalled `accent_text`.
