# Custom pad toolbar

## 2026-10-30: the toolbar spin boxes clip their text in larger theme fonts (#106)

`KSSpinBox` (`widgets/common/button.py`) takes a fixed width from `[keypad.custom] spin_width` (70 px, and 77 for the vGrids / hGrids spin boxes in `CustomPad._insert_toolbar`), while its text uses the app font the theme sets. Offscreen, `CustomPad` in edit mode with both toolbars expanded, `sizeHint().width()` against `width()`:

| theme | font size | width | needed |
|---|---|---|---|
| dark | 9 pt | 70 / 77 | 81 / 80 |
| kitty | 14 pt | 70 / 77 | 118 / 117 |
| sponge, retro | 18 pt | 70 / 77 | 145 / 144 |

In Sponge, `vGrids: 1` renders as `Grids:` with no value and `Rows: 5` as `ows:`; Dark fits only barely.

Fix options, not decided:

- Drop the fixed width and let Qt size the spin box from its font. Needed in any case, since the font family changes the width too (VT323 and Sans Serif differ at the same size). The toolbar is a `FlowLayout`, so controls that do not fit wrap. `spin_width` and the `+ 7` for the grid spin boxes go away. At 18 pt the spin boxes become about 145 px wide.
- On top of that, give the toolbar controls their own font size, apart from the theme's app size, the way `picker_size` does for the picker (family from the theme, size from a theme value or a fixed one), so a large theme font does not make the toolbar huge.
- Scaling the font down to a fixed width was not measured; it keeps the layout fixed but makes the text size depend on the label length.
