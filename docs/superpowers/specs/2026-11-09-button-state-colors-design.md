# Button state colors that work everywhere

Issues: #198, #199, #200. Milestone: First release (#22).

## Why

Every button in a theme has one type, `Button` (`src/tcalc/ui/look.py`). A theme can write all of its color fields in any button table, and the theme loads them, but the stylesheet reads only some of them in each place. A color a theme writes and the app never draws is a setting that silently does nothing: the theme author changes it and sees no change.

The clearest case is the keypad. `[keypad.button]` is where every key starts, and a key kind (`[keypad.operator]`, `[keypad.trig]`...) writes only what differs. The merge already happens when the theme loads (`with_shared_buttons`), so each kind holds its resolved `checked` and `disabled` colors. But `src/tcalc/ui/widgets/keypad/style.qss` styles `:checked` and `:disabled` once for all keys from `$keypad_button_*`, so a kind's own `checked` never reaches the screen. Measured on 2026-11-09: a theme with `[keypad.operator] checked = { color = "mark" }` produces `keypad_operator_checked_color` in the substitutions, and the color is not in the stylesheet.

The theme-areas spec (`2026-11-04-theme-areas-design.md`, "Shared types") decided that "a setting one place does not draw exists there without effect". This spec narrows that decision for colors: a color field of a `Button` is drawn wherever its widget can be in that state.

## Goal

In every `Button` table, these fields reach the screen for each state its widget enters: `color`, `hover_color`, `pressed_color`, `text.color`, `checked.color`, `checked.text_color`, `disabled.color`, `disabled.text_color`.

Inheritance stays as it is. In a theme, `[keypad.button]` is merged into every key kind and `[history.button]` into copy, delete, clear and mode (`with_shared_buttons`); a kind or a button that writes a field overrides that field. One existing exception stays: a keypad kind that writes `color` and no `hover_color` hovers to its own color (`_hover_follows_color`), so a recolored key does not hover to the old color.

## How the keypad kinds map to keys

The look tables and the `keypadRole` values differ in one place. Digit keys have the role `digit`, and custom pad keys the role `custom` (`custom_pad.py:53`); neither has a rule of its own, so both take the base rule `QPushButton[keypadRole]`, which reads `[keypad.number]`. The other kinds have a rule per role. Memory keys have the role `memory` but are styled by `[memory]` in `topbar/style.qss`, outside the keypad.

## What is not drawn today

Measured on 2026-11-09 against `master` (`2e756ce`) by listing each table's color substitutions that no QSS file reads, then reading the widgets. A text color that Python reads as an icon tint counts as drawn (`history.py:384,395`, `result.py:88`).

- **Keypad kinds:** `checked.color`, `checked.text_color`. The only checkable keys are Shift and Hyp (`keypad_defins.py`, `TRIG_KEYS`), so the kind that enters the state is `trig`; the QSS reads `[keypad.button]` instead.
- **History copy and delete:** `hover_color`, `pressed_color`. The QSS reads them from `[history.button]` for both.
- **History clear:** `hover_color`, `pressed_color`. Clear History is an `iconButton` outside the history items, so its hover and pressed come from the generic `QPushButton[uiRole="iconButton"]` rule in `styles/common.qss`, which reads `[palette]` (`highlight_color`, `base_color`). The comment in `history/style.qss` says so: "hover and pressed stay the icon button's".
- **History mode and `[options]`** (both `OptionButton`, a `QRadioButton`): `color`, `pressed_color`. `common.qss` sets their background to a fixed `transparent`.
- **`[custom_pad.add_key]`:** `pressed_color`, `text.color`. The add key is an `IconButton` (`custom_pad.py:303`): its pressed color comes from the generic `iconButton` rule, and its text color is the icon's tint, which Python paints.
- **`[custom_pad.spinbox]`:** `hover_color`. `KSSpinBox:hover` sets only the border.
- **`[menu.item]`:** `color`, `hover_color`, `text.color`, `disabled.color`. `QMenu::item:selected` (hover) and `:checked` share `checked.color`; item text uses `[menu.panel]`; `QMenu::item:disabled` sets only the text color, and disabled items exist (`manubar/defins.py`).

`[memory]` and `[result.fraction]` draw every state their widgets enter and need no change.

## States a widget does not enter

A state rule is written only where the widget can be in that state. Measured in the code on 2026-11-09:

- No keypad key is ever disabled: `KeyDef.enabled = False` appears only in the memory keys (`topbar/defins.py`) and the menus (`manubar/defins.py`). The keypad kinds get no `:disabled` rule, and the existing `QPushButton[keypadRole]:disabled` rule in `keypad/style.qss` reaches no key.
- Only `trig` keys are checked. The other kinds get no `:checked` rule.
- Copy, delete, clear, the fraction toggle, the add key and the spinbox are never checked; history mode, options, copy, delete, clear, the add key and the spinbox are never disabled.

Their `checked` and `disabled` fields keep having no effect, and the template says so. A state is drawn through a pseudo-state Qt documents for that widget; a `QMenu` item has no pressed state, so `[menu.item] pressed_color` stays without effect and the template names it. The builder stops and reports any widget that turns out to enter a state this list says it does not.

## Constraints

- **The bundled themes look the same after the change.** Each newly read field must resolve, in `light`, `dark`, `kitty`, `retro` and `sponge`, to what is drawn there today. The builder compares the substitution values before and after for every bundled theme, and where a default differs from what is drawn, it sets the default in `look.toml` or the theme to the drawn value and lists each change in the PR. Known cases:
  - `[menu.item] hover_color` is `primary` at 0.14 opacity, while hover draws `checked.color` (solid `primary`) today.
  - `[history.clear]` hover and pressed draw `[palette] highlight_color` and `base_color` today.
  - `[options]` and `[history.mode]` draw a `transparent` background today; colors are opaque names, so the drawn value is written as a color at opacity 0.
  - `[custom_pad.add_key]` pressed draws `[palette] base_color` and its icon the palette icon color today.
- **QSS reads the resolved per-kind value.** A rule for a kind reads that kind's substitution (`$keypad_trig_checked_color`), not the shared table's. The shared table needs no rule of its own, since its values reach every kind through the merge.
- **No new field, no new type, no new mechanism.** This is QSS rules over the existing `Button` fields and substitutions, and a `tint` passed to the existing `IconButton` where Python already paints the icon.
- **Rule order.** At equal specificity the later QSS rule wins. In `keypad/style.qss` hover comes first ("Before :disabled, :checked and :pressed"), then the generic `:checked`, then each kind's base and `:pressed` rules, so a pressed checked key shows its pressed color today. A kind's new `:checked` rule keeps that outcome.

## Custom color names (#199, #200)

A theme can add its own names to `[colors]` and use them in any color field; this works today (`ColorName` is a `NewType` over `str`, `theme.py` merges the theme's `[colors]` over its base's, and `_known_colors` logs an unknown name and restores the default). Measured on 2026-11-09: `[colors] sunset_orange = "#FF8800"` with `[keypad.operator] color = "sunset_orange"` gives `background-color: #FF8800` in the operator rule.

`src/tcalc/themes/theme-template.toml` gets a note above `[colors]`: a theme can add its own color names next to the listed ones and use them anywhere a color is named; a name that is in neither the theme's `[colors]` nor its base's is logged and that place keeps its default. That closes #199, and #200: the human agent confirmed on 2026-11-09 that #200 asks for this behavior.

## Template

The template's "Buttons take the same keys everywhere" paragraph is updated: color fields work in every button table for every state its widget enters; the non-color fields of a keypad kind (`radius`, `text.font`, `edge`, `padding`) are read from `[keypad.button]` only and have no effect in a kind's table. The per-table comments name the states a widget does not enter.

`[menu.panel] hover_color` has no effect: a menu row's hover is `[menu.item] hover_color`. The field stays in the `Panel` type, because `[picker]` and `[custom_pad.menu]` draw it (`keypad/style.qss`); the template's `[menu.panel]` comment says it has no effect there.

A field with no effect is only documented. No code, check or log is added to report it; the existing theme loading reports what it already reports (an unknown key, a wrong type, an unknown color name), and nothing more.

## Tests

- `tests/py/e2e/ui/`, on the test themes (`tests/py/e2e/ui/themes/`): each place that gains a state draws the theme's color for it, and a place whose table writes nothing draws its shared table's. One row per place, in one parametrized test.
- `tests/py/e2e/test_bundled_themes.py` stays green.

## Not in scope

- Per-kind `radius`, `text.font`, `edge` and `padding` on the keypad. They are read from `[keypad.button]` only (`widgets/utils.py:103,120`, `keypad.py:216-221`); making them per kind needs the radius fit and font scaling to work per kind. It waits until someone asks for it.
- Renaming `[keypad.operator]` and the other kind tables to `[keypad.button.operator]`. The names stay, so no user theme breaks.
- The format of colors for the theme settings panel.
