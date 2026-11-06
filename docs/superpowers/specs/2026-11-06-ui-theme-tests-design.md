# Python test layers, part 2: the theme tests in `tests/py/ui`

Issue #205, milestone First release (#22). Starts when [part 1](2026-11-06-python-test-layers-design.md) is done.

## Why

`tests/py/ui` is really the e2e of the UI. The theme tests added there lately read the bundled themes, write toml strings into a folder and hand lambdas to rows, and a menu is walked to reach a function. Changing a color in a bundled theme should break no test here.

## Scope

- `tests/py/ui/test_theme_switch.py`, the whole file: it tests only themes.
- `tests/py/ui/test_history.py`: only the `Theme` section (`apply_user_theme` through `test_icon_button_size_applies_to_new_items`).
- `tests/py/ui/test_custom_pad_layout.py`: only `test_toolbar_spin_boxes_keep_their_font_and_fit_under_a_big_app_font` and `test_a_saved_primary_key_keeps_its_color`.
- What part 1 moved to `tests/py/e2e/ui/`: `test_theme_on_widgets.py`, `test_icons_on_themes.py`.
- Last, the rest of `tests/py/ui` moves to `tests/py/e2e/ui/`.

Not touched: `test_expression.py`, `test_controller_status.py`, `test_result_widget.py`, `test_view_state_ui_sync.py`, `test_subscript_constants_ui.py`, the other sections of `test_history.py` and `test_custom_pad_layout.py`, and the other files in `tests/py/e2e/`. `test_subscript_constants_ui.py` keeps its menu walk, since it is not a theme test.

No tool compares the look between two refs. The owner dropped `make ui-diff`: it could only say that pixels changed, never whether they are right.

## The test themes

- `tests/py/ui/themes/dark.toml` and `light.toml`, new. They hold the 32 color names of the bundled `[colors]`, each with a different value within its file, since a black and white theme cannot prove a stylesheet rule (see the finding). `background_dark` is `#000000` in dark and `#FFFFFF` in light, the owner's black and white. The literals the tests already assert are the test themes' own values: `icon` is `#FCFCFC` in dark and `#232629` in light, `background` is `#F4F5F7` in light. `screen` is `#FEFEFE` in light.
- `extreme`, as it is. It is the one custom theme: its base is light, so it also stands where a test needs a custom theme on a light base.
- Nothing else. A case with its own values is a dict row.

Two fixtures make them work, by what the finding measured, with no production change:

- `own_themes` points `tcalc.theme.BUILT_IN_DIR` at that folder. `dark` and `light` then read the test files, and `custom_themes()` lists `extreme`. This replaces the `extreme_theme` fixture.
- `theme_table(table: dict[str, object], base: str = "dark") -> str` patches `tcalc.theme._read` to answer the variant `"user"` with `{"name": "User", "base": base, **table}`, and returns `"user"`. Other variants read their files. `"user"` is not in `custom_themes()`, so a test going through `AppState.theme` uses `extreme`.

Both are autouse for what they serve: an autouse fixture in `tests/py/ui/conftest.py` and in `tests/py/e2e/ui/conftest.py` requests `_user_themes` and `own_themes`. Until the move they live in a new `tests/py/conftest.py`, not autouse there, because two sibling folders use them and `tests/py/unit` must not have them forced on it. The move merges it into `tests/py/e2e/ui/conftest.py` and removes it. The `TODO(test themes)` goes.

A probe with every test of `tests/py/ui` on these themes gave 10 failures, all in the scoped files (see the finding). Nothing outside them depends on the bundled colors.

## `test_theme_switch.py`, test by test

`window` splits: its settings patches, `_app_state` reset and palette restore become a `state` fixture, which `window` requests. `_view_menu`, `_theme_action` and `QMenu` go.

Removed, 4 tests. A menu button is not tested, the function behind it is, and these test only the menu:

- `test_theme_is_first_in_view_menu`, `test_theme_items`, `test_stored_choice_is_checked`: the shape of the menu.
- `test_theme_added_while_running_shows_when_the_menu_opens`: it walked the menu to reach `_populate_custom_themes`.

Removed, 5 more tests, by the owner's decision: this file holds only e2e tests of the chain from a theme table to a widget.

- `test_late_scheme_signal_does_not_reapply`: `test_sync_theme` in the unit layer does the same.
- `test_user_key_colors_survive_switch`: it tests that Qt keeps a plain widget's stylesheet.
- `test_toast_is_styled_by_level_not_inline`, `test_tooltip_window_corners_are_see_through`, `test_main_keypad_restyles_keys_once_per_resize_burst`: nothing to do with a theme switch.

Rewritten to call the function, 2 tests, on `state` with no window:

- `test_set_theme_light_requests_qt_scheme_and_persists`, was `test_choosing_light_...`: `ViewOperations(None).set_theme(ThemeChoice(ThemeMode.LIGHT))` asks Qt for the light scheme and `AppState` keeps the choice.
- `test_set_theme_custom_restyles_without_a_scheme_change`, was `test_choosing_kitty_...`: on `extreme`, the theme is on with no scheme signal, since light and `extreme` share Qt's light scheme.

New, 3 tests, for the function behind the custom theme menu, called directly as `test_active_custom_clears_builtin_checkmarks` calls `_populate_custom_presets`. They read `_custom_theme_actions`, the reference the menu keeps. The `aboutToShow` connection itself stays untested, since reaching the signal means walking the menu.

- `test_populate_custom_themes_shows_a_theme_added_while_running`, `test_populate_custom_themes_checks_the_stored_choice`, `test_custom_theme_action_sets_the_theme`.

Stay as they are, because they name no bundled theme and now run on the test themes:

- `test_widget_stylesheets_set_no_colors`: no widget's own stylesheet holds a color, since that would not follow a theme.
- `test_switch_reaches_hidden_widgets`: a widget hidden during the switch takes the new background. `LIGHT_BASE` stays white, the test light's `background_dark`, and its comment says so.
- `test_keypad_rules_are_scoped`: keypad selectors do not leak out of the keypad role, and no bare `QSpinBox` or `QFrame` rule exists.
- `test_pressing_a_checked_key_shows_its_pressed_color`: a checked and pressed key paints `action_hover`.

Change their theme or their rows, and keep what they check:

- `test_switch_reaches_open_widgets`: after a switch, open widgets take the new background and the stylesheet has no `$` left. `Display` reads `screen`, not `background_dark`: the two only looked like one value because both are white in the bundled light. It compares with a new `LIGHT_SCREEN`, the test light's `screen`, so the test now tells them apart.
- `test_equals_key_paints_the_theme_primary`: the equals key's face is `primary`. Dict table.
- `test_checked_key_paints_primary_with_its_text`: a checked key paints `primary` and `primary_text`. Dict table.
- `test_side_panel_fonts_stay_scaled_after_switch`: fonts stay in their range when the app font is above it. The literal `10` reads `DEFAULT_LOOK.history.clear.text.font.max_pt`.
- `test_font_range_follows_the_theme`: each area's font follows its range, and comes back. A frozen `FontRangeCase(table, widgets, top)`: `table` a dict, `widgets` a named function, `top` a dotted path read from `DEFAULT_LOOK` in place of the literals `12`, `10`, `13`, `32`, `26`, `16`.
- `test_open_fraction_button_takes_the_theme_padding`: the open fraction button takes the theme's padding. Dict table.
- `test_history_takes_the_theme_monospace_font`: the history list takes the theme's monospace family. Dict table.
- `test_dock_titles_and_tabs_follow_the_theme`: dock titles and tabs take their color and size from the theme. Dict table.
- `test_a_radius_above_the_widget_is_as_round_as_it_fits`: a radius above a widget's size draws fully round. `round_theme` builds a dict through `theme_table`, the `window` param is `{"theme": "user"}`, and the lambdas in `shown` become named functions.
- `test_raised_edge_reaches_every_button_area`: the raised edge is painted on every button area. `edged_theme` the same way.
- `test_keys_are_as_round_as_they_fit`, `test_keys_stay_round_while_shrinking`, `test_custom_keys_stay_round_when_the_grid_keeps_its_size`: keys stay round at launch, on resize, on shrink and when the grid keeps its size. `"extreme"` replaces `extreme_theme`.

## The other theme tests

`test_history.py`:

- `apply_user_theme(table: dict[str, object], base: str = "dark")` goes through `theme_table`.
- `test_theme_reaches_the_history`: a frozen `HistoryThemeCase(table, shown, expected)` with named functions in place of the lambdas, the same 15 ids.
- `test_raised_edge_shadow_is_darker_than_the_button`: its table sets the two colors it compares, `background_light` (the face of `history.copy`) and `button_shadow`, because a relation on arbitrary test colors proves nothing. What it checks is which colors the default look paints there. The base changes neither color, so 2 cases become 1.
- `test_checked_mode_button_paints_primary_with_its_text`, `test_open_items_take_the_theme_sizes`, `test_icon_button_size_applies_to_new_items`: dict tables.

`test_custom_pad_layout.py`:

- `test_toolbar_spin_boxes_keep_their_font_and_fit_under_a_big_app_font`, was `..._in_every_theme`: the app font changes under the spin boxes, and they keep theirs. Its table is `{"fonts": {"size_default": 30}}`, so 3 cases become 1. No family: the only other font is `VT323` in the bundled retro folder, which the test themes do not register, so the name resolves to a fallback.
- `test_a_saved_primary_key_keeps_its_color`: `dark`, `light`, `extreme`, so 5 cases become 3.

`tests/py/e2e/ui/test_theme_on_widgets.py`:

- `write_theme` calls become `theme_table`, and `write_theme` leaves the conftest.
- `test_every_qss_placeholder_resolves`: `dark`, `light`, `extreme`, so 5 cases become 3.
- `test_light_scheme_sets_light_palette` keeps `#F4F5F7`, the test light's value.

`tests/py/e2e/ui/test_icons_on_themes.py`:

- `test_kitty_uses_its_base_variant_files` becomes `test_custom_theme_uses_its_base_variant_files`, on `extreme`.
- `#fcfcfc` and `#232629` are the test themes' `icon`. `#da4453` is the icon file's own color and stays.

## The bundled themes

New file, `tests/py/e2e/test_bundled_themes.py`, by the owner's decision: nothing else catches a broken bundled theme, since the app only logs it and falls back. It is outside `tests/py/e2e/ui` because that folder's tests run on the test themes. It runs on `dark`, `light` and each `*/theme.toml` of the bundled folder.

- `test_bundled_theme_loads_with_nothing_skipped`: broken toml raises, and an unknown key, an alpha color or a place naming a missing color logs a warning.
- `test_bundled_theme_names_only_the_colors_of_dark`: `dark` and `light` have the same names, and a custom theme adds none.
- `test_bundled_theme_pictures_exist`, `test_bundled_theme_resolves_every_qss_placeholder`.
- `test_theme_template_holds_only_known_keys`: the settings of `theme-template.toml`, uncommented, load with nothing skipped.
- `test_test_themes_name_the_bundled_colors`: the test `dark` and `light` hold a copy of the bundled color names, so this is the check that fails when the copies drift.

## The move

The last step. `tests/py/e2e/ui/` already exists from part 1, so `git mv tests/py/ui tests/py/e2e/ui` would nest it: the test files and `themes/` move one by one. `tests/py/ui/conftest.py` and `tests/py/conftest.py` merge into `tests/py/e2e/ui/conftest.py` and go, and `own_themes` folds into its autouse `_test_themes`. The `makefile` loses its `tests/py/ui` line, and `py-test-ui` follows. `tests/py/e2e/conftest.py` now loads for all of it: its `QT_LOGGING_RULES` default wins over the ui one, which only quiets more logs, and its `_reset_canon_log` does nothing for a module with no `CANON_LOG`. The last step greps the whole tree for the old path.

## Rules

The layers section of `docs/rules/ai/tests.md` names `tests/py/e2e/ui`.

## Done when

- `make py-test`, `make py-lint` and `make typecheck` pass. The case counts match: `test_theme_switch.py` has its 9 removed tests fewer (13 cases) and 3 new, the spin box test 2 cases fewer, the shadow test 1, the saved key test 2, the placeholder test 2, and `test_bundled_themes.py` is new with 23 cases. Any other difference is reported.
- `grep -rnE '"(kitty|retro|sponge)"' tests/py` finds nothing: `test_theme_readability.py` lists the bundled themes with a glob.
- `grep -rnE '\.menu\(\)|\.actions\(\)' tests/py/e2e/ui/test_theme_switch.py` finds nothing.
- Changing a color in a bundled theme leaves `make py-test` green, apart from `test_theme_readability.py` if it hurts contrast. A broken one fails `test_bundled_themes.py`.
- `grep -rn 'tests/py/ui' .` finds only recorded findings and specs.
