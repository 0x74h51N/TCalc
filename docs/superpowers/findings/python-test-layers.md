# Python test layers

## 2026-11-06, master f8a67cd: what the widgets and the fake depend on

Which modules load the real native module on import (`'calc_native' in sys.modules` after `importlib.import_module`): `tcalc.typed_tables`, `theme`, `ui.look`, `ui.props`, `ui.icon`, `ui.utils`, `ui.config` do not. `ui.styles`, `ui.controller.utils` and every module under `ui.widgets` do.

Widgets need the native module's tables and names at import, not its engine. Today's fake in `tests/py/unit/core/conftest.py` fails on them only because it has fallen behind: `AttributeError: ... 'LatexKind'`, then `LatexExpr.Subscript` (its latex table has an old `ExprKind` with `Frac`, `Pow`, `Root`), then `Operation.MUL` (19 op ids against the real 53).

With a throwaway fake holding the real op, constant and latex tables and enums as plain Python, every file of `tests/py/unit/ui` except `test_format_result.py` passes: `test_common_widgets` 20, `test_picture_layer` 16, `test_props` 130, `test_styles` 17, `test_icons` 47, `test_color_scheme` 26, `test_theme_colors` 48, `test_look` 3, `test_typed_tables` 25, `test_theme_overrides` 30, which is 362 of the 385. The names it had to stand in for beyond those tables only need to exist: `ParenSplit`, `LatexSplit`, `structural_split`, `split_operand`. The probe copied its tables from the real module at start, then dropped it from `sys.modules`; a real fake has to hold them as data.

Importing `tcalc.core.ops` and `tcalc.core.utils` alone reads these names from the fake: `ConstId`, `OpId`, `const_table`, `latex_exprs`, `op_table`, `BigReal`, `BigComplex`, `Rational`, `Collection`. This is measured at import with a recording proxy, not over a test run.

## 2026-11-06, master f8a67cd: bundled themes can be swapped with no production change

With `tcalc.theme.BUILT_IN_DIR` set to a folder holding a `dark.toml` and `light.toml` with the same 32 color names and invented values, `load_theme("dark")` gives `look == DEFAULT_LOOK` and `custom_themes()` gives `{}`. With `tcalc.theme._read` replaced to answer `"user"` with a dict, `load_theme("user")` applies it and logs `theme user.keypad: expected a table, got list` for a table no single toml file could hold beside `[keypad.number]`. Both run through a throwaway script, with `src/` untouched.

With every test of `tests/py/ui` on those invented `dark` and `light` through an autouse plugin: 13 failed, 1287 passed, 12 xfailed, 4 xpassed. The failures: `test_theme_switch.py` 5, `test_custom_pad_layout.py` 6 (the bundled theme names), `test_history.py` 2 (`test_raised_edge_shadow_is_darker_than_the_button`, on arbitrary colors). Nothing outside the theme tests depends on the bundled colors.

## 2026-11-06, master f8a67cd: the theme switch runs with no window and no menu

`apply_theme`, `sync_theme` and `ViewOperations(None).set_theme` all run on the fake `calc_native` and two dumb themes (every color name black or white), with `QStyleHints.setColorScheme` recorded: 3 passed. With `app.setPalette(_build_palette())` removed on a scratch copy of `src/`: 3 failed. `set_theme` never touches the window it is built with.

## 2026-11-06, master f8a67cd: each loader function runs alone

Called directly on the fake `calc_native` and the dumb themes, with no `Theme(...)` in the way unless it is the subject (`QT_QPA_PLATFORM=offscreen PYTHONPATH=src:.:<plugin dir> .venv/bin/python <probe>`):

- `_opaque({"a": "#000000", "b": "rgba(1,2,3,50%)", "screen": "qlineargradient(x)"}, "t")` keeps `a` and `screen`, logs `t [colors].b: 'rgba(1,2,3,50%)' is not an opaque color`.
- `_convert_keys([1], ...)` gives `({}, [TableError('w: expected a table, got list')])`.
- `values({"a": "x", "b": 5}, str, "w")` gives `{'a': 'x'}`, logs `w.b: expected str, got int`.
- `_merged` gives `{'color': 'b'}` and `{'x': 1, 'y': 2}`. `_hover_follows_color` gives `{'color': 'a', 'hover_color': 'a'}` and `5`. `with_shared_buttons({"keypad": [1]})["keypad"]` stays `[1]`.
- On a `Theme("dark")`: `_pictures("x", "w")` is `()`, logs `w: expected a list, got str`; a bad fit logs `w #2.fit: expected PictureFit, got str 'fill'`; `_known_colors` restores the default, logs `w.picker.text.color: 'nope' is not one of its colors`.
- `_read` on `bad-toml` raises `ThemeError`.
- `_build_stylesheet` with `_QSS_FILES` patched printed `x { c: $background_color; d: $nope; }`: `$background_color` is not replaced, because look fields are named by place (`display_background_color`). A test has to use a real `qss_name`.

## 2026-11-06, master f8a67cd: a black and white theme cannot prove a stylesheet rule

A `QPushButton` with `keypadRole`, inside and outside a `QWidget[uiRole="keypad"]`, on the dumb themes: both read `#000000` on dark and `#fcfcfc` on light. The bare key gets no keypad rule at all, so the same pixel proves nothing. With `secondary = "#FF0000"` the key inside reads `#fc7373`: the rule applies, and the color is blended over the style's own button base. A look test needs a theme with a distinct color per place.

With `calc_native` blocked (`sys.modules["calc_native"] = None`), each `tests/py/unit/ui` file: `test_icons` 47 passed, `test_look` 3 passed, `test_typed_tables` 25 passed. The rest fail at import, through `styles.py:10 > app_state.py:13`, `tcalc/ui/widgets/__init__.py:23`, or `tcalc/core/__init__.py:24`. On a scratch copy, removing the one line `from ..app_state import get_app_state` lets `tcalc.ui.styles` load and `apply_theme` run with native blocked. `get_app_state` is used there only in `sync_theme`.

Tried and removed, 2026-11-06: a look test (`apply_theme`, then a plain widget's palette after `ensurePolished`, on a theme with a color per place) with `sync_theme(app, variant)` changed to make `styles.py` load with no native. It works, and it reads a key's exact color, but it runs the whole chain from toml to widget, so a failure names no function. That is an e2e test. The human agent declined it for the unit layer, and the source change was undone with it.

## 2026-11-06, master f8a67cd: the small functions under styles and widgets run alone

Called alone with plain inputs and nothing under `src/` changed: `qss_color("#123456", 0.5)` gives `rgba(18, 52, 86, 50%)`, `fit_radius(w, "x", 99, 20, None)` gives `10`, `set_raised(w, True)` sets the property, `reposition` gives `180 140`, `picture_rects` on a `SimpleNamespace` picture gives the two rects. `shortest_side([w])` gave `None` on a widget that was not shown: it skips hidden widgets, so its test shows the widget.

## 2026-11-06, master f8a67cd: a function that branches on a type can run on fake types

`look_fields` reads `ColorName`, `ColorRef` and `Tinted` from its module when called, so `monkeypatch.setattr("tcalc.ui.look.ColorName", FakeColor)` and the like let a test use only its own types, with `from tcalc.ui.look import look_fields, qss_name` as its one production import. 2 passed, `calc_native` not loaded. Removing the tinted branch, the bare ref arm or the color arm on a scratch copy each gave 1 failed, 1 passed.

## 2026-11-06, test/python-test-layers 4d47f3d: part 2's themes, probed from a scratch plugin

Themes as part 2's spec says (32 distinct colors per file, `background_dark` black and white), with `BUILT_IN_DIR` patched by an autouse plugin and `src/` and `tests/` untouched: `.venv/bin/python -m pytest -p part2_plugin tests/py/ui -q` gave 10 failed, 1290 passed, 12 xfailed, 4 xpassed. The failures: `test_toolbar_spin_boxes_keep_their_font_and_fit_in_every_theme` 3, `test_a_saved_primary_key_keeps_its_color` 3 (the bundled names), `test_raised_edge_shadow_is_darker_than_the_button[dark]`, `test_switch_reaches_open_widgets`, `test_theme_items`, `test_choosing_kitty_restyles_without_a_scheme_change`.

`test_switch_reaches_open_widgets` fails for a reason of its own: `Display` reads `screen`, the side panel `background_dark`, and both are `#FFFFFF` in the bundled light, so the test never told them apart.

The tests part 1 moves, at their old paths on the same plugin: 4 failed, 67 passed, all by bundled name (`test_kitty_uses_its_base_variant_files`, `test_every_qss_placeholder_resolves` 3).

The planned shapes, in a scratch test file: 16 passed. `ViewOperations(None).set_theme` on `LIGHT` and on `extreme`; the spin box rows on `theme_table({"fonts": {"family_default": "VT323", "size_default": 30}}, base)`; the saved key on `dark`, `light`, `extreme`; the `DEFAULT_LOOK` dotted paths; `custom_themes()` listing only `extreme`. The raised edge rows with `background_light = "#C0C0C0"` and `button_shadow = "#101010"` read shadow `#66645f` on dark and `#898989` on light against face `#c0c0c0`. Whether the spin box rows catch a broken font is not measured yet: part 2's plan does that.

## 2026-11-06, master f8a67cd: baselines

```bash
for d in unit/core unit/ui ui e2e; do PYTHONPATH=src .venv/bin/python -m pytest tests/py/$d -q | tail -1; done
```

`unit/core` 24 passed, `unit/ui` 385 passed, `ui` 1300 passed, 12 xfailed, 4 xpassed, 115 warnings, `e2e` 407 passed.

`make typecheck` covers `files = ["src"]` only. Over tests, `.venv/bin/python -m mypy --check-untyped-defs tests/py/<dir>` reports 5 errors in `unit/core`, 29 in `unit/ui`, 28 in `ui`, 2 in `e2e`; over all of `tests/py` it stops with `errors prevented further checking`.

## 2026-11-06: unit tests that passed on broken code

Found by breaking a scratch copy of `src/` one line at a time and running the file against it, branch `test/python-test-layers`.

- `test_empty_box_is_not_rendered` passed with `if rect.isEmpty()` removed: it asserted before the pool ran the job. It now calls `QThreadPool.globalInstance().waitForDone()` first.
- The pruning at the end of `PicturePainter.paint` is not reached by a theme with no pictures, which returns early. It needs a picture left out while another stays.
- `1.9999999999999998` does not reach the `"999999999999"` branch of `format_result`: `.16g` already rounds it to `2`. `1.9999999999999991` does.
- `get_icon(None).isNull()` holds without the `None` check unless `theme_icon` is patched to return a real icon.
- A whole `Rational` of `6` formats the same through `to_double()`. `10**16 + 1` tells the exact path apart.

## 2026-11-06: a widget fixture can read the real theme after its patch is gone

`widget.deleteLater()` followed by `qapp.processEvents()` does not delete the widget, so its timers stay alive. The fit timer of `OptionGroup` then fired during `test_format_result[big complex]`, on the real `get_theme` (`button.py:178 _fit_radius`). `qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)` in the fixture's teardown deletes it while the patch still holds.

`format_result(1e-7)` shows `9.9999999999999995e-08` to the user: `fmt_real` uses `.16e` below `1e-6`. Not changed; the test row uses `2**-24`, which prints exactly.

## 2026-11-06, test/python-test-layers: removal probes read stale bytecode

Rewriting `tests/py/unit/core/conftest.py` in a loop and running after each change gave `calc_native.ConstSpec` as needed, right after `ConstId`, whose line has the same length. With bytecode off, removing `ConstSpec` gives 12 passed and removing `ConstId` gives 2 errors. The likely cause, not proven, is a `.pyc` taken as current for a file of the same size written in the same second. Run such probes with bytecode off:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/py/unit/core -q
```
