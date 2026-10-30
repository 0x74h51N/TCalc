# Theme radius

## 2026-10-30: a radius above half the short side gives square corners

Qt draws a `border-radius` only when it is at most half of the widget's shorter side; above that it draws square corners, with no warning. Measured on `feat/theme-switching` with plain `QPushButton`s (offscreen, PySide6), stylesheet `border-radius: <r>px`:

| radius | 40x55 | 50x50 | 52x52 | 60x60 | 145x130 | 178x360 |
|---|---|---|---|---|---|---|
| 25 | square | round | round | round | round | round |
| 90 | square | square | square | square | square | square |

Consequences seen in the app:

- `radius_small = 90` turns every key square.
- In Sponge (`radius_small = 25`), narrow custom pad keys (about 40 px wide) are square while the large keys of another custom pad are round. It looked like old keys versus new keys; it is key size.

False hypothesis: custom pad keys do not get the keypad rule. They do: `CustomPad` sets `uiRole="keypad"` and its keys carry `keypadRole="custom"`, and a probe showed plain and colored custom keys rounded at 25 px, also after a theme switch with the keys open.

## 2026-10-30: the key radius at launch is fitted to the default key size

`apply_key_radius` ran from the keypad's and the custom grid's `resizeEvent`, which comes before the layout gives the keys their size. At launch the keys still had Qt's default 100x30, so the radius was 15 everywhere: square main keypad keys (21 of 23 with a radius above half their side) and custom keys of 43x96 at 15 instead of 21. A resize after launch fixed it. Running the fit from a 30 ms single-shot timer that each resize restarts (`[keypad] resize_debounce_ms`) gives the layout time to size the keys, and collapses a drag into one fit.

Offscreen probe, `MainWindow` with a copy of Sponge and three custom grids, 40 resizes of 6x3 px, `-p no:randomly`:

| tree | radius | `apply_scaled_fonts` calls | `apply_key_radius` calls | `apply_key_radius` time |
|---|---|---|---|---|
| master 709667e | 50 | 39 | (none) | |
| per-resize fit (stash) | 50 | 39 | 75 | 10.7 ms, 96 `StyleChange` |
| debounced fit | 50 | 1 | 4 | 13.7 ms once after the drag |

## 2026-10-30: a debounced radius squares the keys while they shrink

With a theme radius above what the keys fit, the fit sets the radius to exactly half the shortest key side. A shrink of one or two pixels leaves that radius above half the new side, so Qt draws square corners until the debounce fires (seen in the app on custom keys during a drag). Offscreen, a custom dock widened to 54 px keys (radius 26) and narrowed by 4 px had 5 of 11 keys square before the timer and none after it; a standalone `MainKeypad` shrunk from 400 to 380 px had 6 square keys. Growing never does it: the old radius still fits. So `resizeEvent` refits at once only when the fitted radius drops below the applied one (`shrink_key_radius`), and growth waits for the timer.

Same drag probe as above, every step a shrink (the worst case), `shrink_key_radius` calls:

| radius | calls | time | `StyleChange` |
|---|---|---|---|
| 5 | 75 | 3.7 ms, no restyle | none |
| 50 | 75 | 22.6 ms over the 40 steps | 202 |
