# Theme picture rendering

## 2026-10-30: a resize that pauses re-renders the theme SVGs, about 120 ms to 340 ms each

`PicturePainter.paint` renders a picture again (`_render`, `QImageReader.read` of the SVG at the new size) once the owner has not been resized for `SETTLE_MS` (150 ms). A drag that pauses longer than that between moves pays a full render of every picture whose box changed. In Sponge the largest is `undersea.svg` (849 KB, target `window`); `holes.svg` covers the display and the history.

Real app, Sponge with `radius_small = 50`, window dragged for a few seconds (cProfile, branch `fix/keypad-key-radius` on 709667e with the key radius change uncommitted):

```
.venv/bin/python -m cProfile -o resize.prof -m tcalc
```

- `QImageReader.read`: 14 calls, 4.76 s, about 340 ms each, all from `picture_layer.py:71(paint)` through `_render`.
- `setStyleSheet` from `apply_key_radius`: 141 calls, 0.33 s. `apply_key_radius`: 0.38 s in all.
- `PictureLayer.eventFilter` shows 17.98 s own time with 0.07 s cumulative and recursion (5848/5820 calls); cProfile misattributes it, it is not a measurement.

Offscreen probe, `MainWindow` with a copy of Sponge and three key grids in docks, 12 resizes of 20x10 px with 200 ms of event processing after each (so the settle timer fires), `-p no:randomly`:

| tree | radius | `_render` calls | `_render` time | busy per step, mean / max |
|---|---|---|---|---|
| master 709667e | 5 | 18 | 2242 ms | 332 / 394 ms |
| master 709667e | 50 | 18 | 2191 ms | 327 / 371 ms |
| key radius fix | 5 | 21 | 2210 ms | 328 / 386 ms |
| key radius fix | 50 | 21 | 2171 ms | 326 / 376 ms |

The stall after a pause is the picture render, on master as well; the key radius fix adds 3 renders (its style change resizes the pads once more) and about 9 ms of `apply_key_radius` with 96 `StyleChange` events at radius 50.
