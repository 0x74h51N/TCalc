# Button State Colors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every color field of a `Button` table reaches the screen for each state its widget enters, and the template documents custom color names.

**Architecture:** QSS rules in the existing stylesheet files read each place's own resolved substitution (`$history_copy_hover_color`) instead of a shared table's or the palette's; one `tint` is passed to an existing `IconButton`; `look.toml` defaults are set to what is drawn today so the bundled themes do not change. No new field, type, check or log.

**Tech Stack:** PySide6 QSS, `look.toml`, pytest e2e UI tests.

**Spec:** `docs/superpowers/specs/2026-11-09-button-state-colors-design.md`

## Global Constraints

- The bundled themes (`light`, `dark`, `kitty`, `retro`, `sponge`) look the same after the change (Task 0 baseline, Task 7 comparison).
- A state rule is written only where the widget enters that state; no rule for `checked` or `disabled` that no widget reaches.
- A rule for a place reads that place's substitution; a shared table (`[keypad.button]`, `[history.button]`) needs no rule of its own.
- No new field, no new type, no new mechanism, no new check or log for a field with no effect.
- Tests run on the test themes in `tests/py/e2e/ui/themes/` or a `theme_table` override; no test reads a bundled theme.
- Hover cannot be painted offscreen (findings, `typed-config.md`, 2026-11-09): a hover test reads `_build_stylesheet()`; checked, disabled, pressed (`setDown(True)`) and a menu item's hover (`setActiveAction`) are read from pixels.
- No commit without the human agent's approval: each commit step stops, shows the diff and waits.

## Review Focus

- A checked key that is also pressed shows its pressed color (`test_pressing_a_checked_key_shows_its_pressed_color` stays green; Task 1's new rule sits before the trig `:pressed` rule).
- A checked menu item that is hovered: checked wins, as on the keypad (Task 5 orders `:selected` before `:checked`).
- A theme that writes only the shared table (`[keypad.button] checked`, `[history.button] hover_color`) reaches every place under it (an inheritance row in Tasks 1 and 2).
- A theme whose `[palette]` differs from its button tables: Clear History and the add key now follow their own tables, so Task 7's comparison covers every bundled theme, not only `dark`.
- Hovering a menu item keeps a readable text: there is no hover text field, so `:selected` keeps `checked.text_color` as today (Task 5).

## Shared test shape

Tasks 1 to 5 add rows to two parametrized tests in `tests/py/e2e/ui/test_theme_switch.py`, created in Task 1. That file holds the `window` fixture (a `MainWindow` with the custom pad dock shown) and the existing key paint tests (`test_checked_key_paints_primary_with_its_text`, `test_pressing_a_checked_key_shows_its_pressed_color`); `theme_table` comes from `tests/py/e2e/ui/conftest.py`.

- `test_theme_state_color_paints(row)`: `apply_theme(qapp, theme_table(row.table))`, finds the widget by `row.place`, puts it in `row.state`, grabs it and asserts the pixel at `(width // 8, height // 2)` (inside `actionGeometry` for a menu item) equals the color `row.color` names in the theme.
- `test_theme_hover_color_reaches_stylesheet(row)`: applies the table and asserts that `_build_stylesheet()` has a rule whose selector list contains `row.selector` exactly and whose block declares `background-color` (or `background`) as the color `row.color` resolves to.

Rows are frozen dataclasses (`PaintRow(id, table, place, state, color)`, `HoverRow(id, table, selector, color)`), with the tuple documented once at the head of each table. `place` is a `Place` enum and `state` a `State` enum (`PLAIN`, `PRESSED`, `CHECKED`, `MENU_ACTIVE`, `MENU_DISABLED`); a fixture maps each `Place` to its widget: keys, options, history buttons and modes from `window`; the add key from `window`'s custom pad after it enters edit mode; menu places from a plain `QMenu` built in the test (an enabled and a disabled action), not from the menu bar (tests.md: no walking of `.menu()` or `.actions()`). Rows hold no lambdas and no toml strings. Each table override uses a custom color name in `[colors]` (for example `mark = "#123456"`), which also exercises #199.

### Task 0: Baseline of the bundled themes

**Files:**
- Create (scratchpad, not the repo): `bundled_look.py`, `bundled_look_before.json`

- [ ] **Step 1: Write `bundled_look.py`**: for each bundled theme, `load_theme(variant)` and resolve, through `_build_subs()`, the substitution each place and state in the spec's "What is not drawn today" list draws. Two maps of place to substitution name: `BEFORE` (what the QSS reads today: `trig.checked -> keypad_button_checked_color`, `clear.hover -> palette_highlight_color`, `add_key.pressed -> palette_base_color`, `add_key.text -> palette_icon_color`, `menu_item.hover -> menu_item_checked_color`, `menu_item.text -> menu_panel_text_color`, `spinbox.hover -> custom_pad_spinbox_color`, `custom_pad_menu_item.color -> custom_pad_menu_background_color`...; a fixed `transparent` is written as the literal) and `AFTER` (the place's own substitution). Run with `BEFORE` now and with `AFTER` in Task 7. Output: JSON `{theme: {place.state: value}}`. No pixels: pixels are the tests' job, this compares values.
- [ ] **Step 2: Run it on the branch before any change**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src python <scratchpad>/bundled_look.py > <scratchpad>/bundled_look_before.json`
Expected: one entry per bundled theme, no `None` values.

### Task 1: Trig keys draw their own checked color

**Files:**
- Modify: `src/tcalc/ui/widgets/keypad/style.qss:42-51`
- Test: `tests/py/e2e/ui/test_theme_switch.py`

- [ ] **Step 1: Write the failing test rows**: create the two tests and their tables (shape above), with paint rows `trig-checked` (`{"colors": {"mark": "#123456"}, "keypad": {"trig": {"checked": {"color": "mark"}}}}`, Shift, `CHECKED`, `mark`) and `trig-checked-from-button` (same under `"button"`).
- [ ] **Step 2: Run, expect `trig-checked` to FAIL** (pixel is `primary`, not `#123456`); `trig-checked-from-button` passes already.

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/ui/test_theme_switch.py -k state_color -v`

- [ ] **Step 3: Replace the generic `QPushButton[keypadRole]:checked` rule** with `QPushButton[keypadRole="trig"]:checked` reading `$keypad_trig_checked_color` and `$keypad_trig_checked_text_color`, placed before the trig `:pressed` rule. Delete the `QPushButton[keypadRole]:disabled` rule: no keypad key is disabled. The raised-edge rule's `:checked` selector stays (edge is out of scope).
- [ ] **Step 4: Run the file and `tests/py/e2e/ui/test_theme_switch.py`, expect PASS**

Run: `PYTHONPATH=src python -m pytest tests/py/e2e/ui/test_theme_switch.py -q`

- [ ] **Step 5: Commit step**: show the diff, wait for approval, then `git commit -m "fix/theme: trig keys draw their own checked color"` with the two files.

### Task 2: History buttons draw their own hover and pressed colors

**Files:**
- Modify: `src/tcalc/ui/widgets/history/style.qss` (the `iconButton` and `#clearHistory` rules), `src/tcalc/ui/look.toml` (`[history]` `clear`, the `[history.button]` comment)
- Test: `tests/py/e2e/ui/test_theme_switch.py`

- [ ] **Step 1: Add rows**: paint rows `copy-pressed`, `delete-pressed`, `clear-pressed` (`PRESSED`); hover rows `copy-hover`, `delete-hover`, `clear-hover` with selectors `QWidget#historyItem QPushButton#historyCopy:hover`, `QWidget#historyItem QPushButton#historyDelete:hover`, `QPushButton#clearHistory:hover` (an id selector, so it outranks the generic `QPushButton[uiRole="iconButton"]:hover` in `common.qss`); plus `copy-hover-from-button` (written under `[history.button]`).
- [ ] **Step 2: Run, expect the copy, delete and clear rows to FAIL.**
- [ ] **Step 3: Implement**: per-button `:hover` and `:pressed` rules for `#historyCopy` and `#historyDelete` reading `$history_copy_*` and `$history_delete_*` (the shared `iconButton` hover and pressed rules inside `#historyItem` keep only the edge colors), and `#clearHistory:hover` and `:pressed` reading `$history_clear_*`; replace the `:!hover:!pressed` workaround where the new rules make it redundant and update its comment. In `look.toml`, set `clear` `hover_color = "primary"` and `pressed_color = "background_dark"` (today's `[palette] highlight_color` and `base_color`), and change the `[history.button]` comment from "read from here" to where the buttons start.
- [ ] **Step 4: Run the file and `tests/py/e2e/ui/test_history.py`, expect PASS.**
- [ ] **Step 5: Commit step**: `fix/theme: history buttons draw their own hover and pressed colors`.

### Task 3: Options and history modes draw their color and pressed color

**Files:**
- Modify: `src/tcalc/ui/styles/common.qss` (`QRadioButton[optionRole="option"]`), `src/tcalc/ui/widgets/history/style.qss` (`#historyModes`), `src/tcalc/ui/look.toml` (`[options]`, `[history.mode]`)
- Test: `tests/py/e2e/ui/test_theme_switch.py`

- [ ] **Step 1: Add paint rows** `options-color` and `mode-color` (`PLAIN`, an unchecked option), `options-pressed` and `mode-pressed` (`PRESSED`).
- [ ] **Step 2: Run, expect the four rows to FAIL.**
- [ ] **Step 3: Implement**: `background-color: $options_color` in place of `transparent`, a `:pressed` rule reading `$options_pressed_color` after `:hover` and before `:checked`, and the same under `#historyModes` with `$history_mode_*`. In `look.toml`, `[options] color` and `[history.mode] color` become `{ color = "background", opacity = 0 }`, which is today's `transparent`.
- [ ] **Step 4: Run the file, expect PASS.**
- [ ] **Step 5: Commit step**: `fix/theme: options and history modes draw their color and pressed color`.

### Task 4: Custom pad add key and spin box

**Files:**
- Modify: `src/tcalc/ui/widgets/keypad/style.qss` (`addButton`, `KSSpinBox`), `src/tcalc/ui/widgets/keypad/custom_pad.py:303` and `:347` (the two `IconButton(...)` calls), `src/tcalc/ui/look.toml` (`[custom_pad.add_key]`, `[custom_pad.spinbox]`)
- Test: `tests/py/e2e/ui/test_theme_switch.py`

- [ ] **Step 1: Add rows**: paint row `add-key-pressed` (`PRESSED`); hover row `spinbox-hover` (selector `KSSpinBox:hover`); an icon tint row `add-key-icon` following `test_history.py:493` (some icon pixel has the tint color).
- [ ] **Step 2: Run, expect the three rows to FAIL.**
- [ ] **Step 3: Implement**: `QPushButton[addButton="true"]:pressed` reading `$custom_pad_add_key_pressed_color`; a `KSSpinBox:hover` rule of its own with `background-color: $custom_pad_spinbox_hover_color` (today `KSSpinBox:hover, KSSpinBox:focus` share one rule that sets only the border; a focused spin box is not hovered, so the background goes in a hover-only rule and the shared border rule stays); pass `tint=lambda look: look.custom_pad.add_key.text.color` to both `IconButton` calls, as `history.py:384` does. In `look.toml`, `[custom_pad.add_key]` `pressed_color = "background_dark"` and `text.color = "icon"`, `[custom_pad.spinbox]` `hover_color = "control"` (all today's drawn values).
- [ ] **Step 4: Run the file and `tests/py/e2e/ui/test_custom_pad_layout.py`, expect PASS.**
- [ ] **Step 5: Commit step**: `fix/theme: the custom pad add key and spin box draw their own colors`.

### Task 5: Menu items draw their own colors

**Files:**
- Modify: `src/tcalc/ui/manubar/style.qss`, `src/tcalc/ui/look.toml` (`[menu.item]`)
- Test: `tests/py/e2e/ui/test_theme_switch.py`

- [ ] **Step 1: Add paint rows** `menu-item-color` (`PLAIN`), `menu-item-hover` (`MENU_ACTIVE`), `menu-item-disabled` (`MENU_DISABLED`, a disabled action), on a `QMenu` with plain actions.
- [ ] **Step 2: Run, expect the three rows to FAIL.**
- [ ] **Step 3: Implement**: `QMenu::item` gets `background: $menu_item_color` and `color: $menu_item_text_color`; split the shared rule into `QMenu::item:selected` (`background: $menu_item_hover_color`, `color: $menu_item_checked_text_color` as today, since a `Button` has no hover text field) followed by `QMenu::item:checked` (checked colors); `QMenu::item:disabled` adds `background: $menu_item_disabled_color`. `QMenu::item` applies to every `QMenu`, and the custom pad menu (`QMenu[customPadMenu="true"]`) draws its own `[custom_pad.menu]` panel: give it `QMenu[customPadMenu="true"]::item { background: $custom_pad_menu_background_color; color: $custom_pad_menu_text_color; }` so its items keep today's look (its `:selected` rule already exists). In `look.toml`, `[menu.item] hover_color = "primary"` (today hover draws `checked.color`).
- [ ] **Step 4: Run the file and `tests/py/e2e/ui/test_view_state_ui_sync.py`, expect PASS.**
- [ ] **Step 5: Commit step**: `fix/theme: menu items draw their own colors`.

### Task 6: Template

**Files:**
- Modify: `src/tcalc/themes/theme-template.toml`

- [ ] **Step 1: Write the custom color note above `# [colors]`** (#199), as the spec words it, with the `sunset` example.
- [ ] **Step 2: Rewrite the "Buttons take the same keys everywhere" paragraph** as the spec's "Template" section says, and add to each affected table's comment the states it does not enter: keypad kinds other than `[keypad.trig]` are never checked and no key is disabled; copy, delete, clear, the add key and the spin box are never checked or disabled; history mode and options are never disabled; `[menu.item] pressed_color` and `[menu.panel] hover_color` have no effect.
- [ ] **Step 3: Copy the changed defaults from `look.toml` into the template's commented defaults** (Tasks 2 to 5), so the template stays a partial copy of `look.toml`.
- [ ] **Step 4: Run** `PYTHONPATH=src python -m pytest tests/py/e2e/test_bundled_themes.py -q`, expect PASS.
- [ ] **Step 5: Commit step**: `docs/theme: custom color names and which button states draw`.

### Task 7: Bundled themes unchanged, whole suite

- [ ] **Step 1: Run Task 0's script again with `AFTER`** into `bundled_look_after.json` and diff it with `bundled_look_before.json`.
Expected: no difference. Any difference: set that default or that bundled theme's value to the before value, record it for the PR, and rerun. A difference that cannot be kept the same is reported to the human agent.
- [ ] **Step 2: Run the app** (`python -m tcalc`) on `dark`, `light` and `retro`: hover a history copy button, the Clear History button, a menu item and an option; check Shift. They look as before.
- [ ] **Step 3: Run** `make py-lint-fix`, `make typecheck`, `make py-test`. Expected: all green.
- [ ] **Step 4:** The PR body names every default changed in `look.toml` and every bundled theme value changed in Step 1, says `Closes #198`, `Closes #199`, `Closes #200`, and `**Breaking:** no`.
