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
