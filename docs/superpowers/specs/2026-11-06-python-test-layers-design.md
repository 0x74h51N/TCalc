# Python test layers, part 1: `tests/py/unit/ui`

Issue #205, milestone First release (#22). The first and main part. Part 2 is [the theme tests in `tests/py/ui`](2026-11-06-ui-theme-tests-design.md), part 3 is [`tests/py/unit/core`](2026-11-06-unit-core-tests-design.md). Measurements: [python-test-layers.md](../findings/python-test-layers.md).

## Why

`tests/py/unit/ui` is called unit and is not. One test pushes a toml through the whole loader and asserts what comes out, so a failure names no function. Tests read the bundled themes and imports pile up.

## What a unit test is here

The owner's definition is the rule now: [tests.md](../../rules/ai/tests.md#what-a-unit-test-is), with the row rule under its Cases section. It is not repeated here. Every test below is held to it.

## Goals

- The functions below are each tested alone, and the ones with no test today get one.
- Every test in the folder is checked against the rule above: kept, rewritten or deleted.
- No test here reads a bundled theme, apart from the readability file.
- Each file passes alone and in any order, with no new package and no production change.
- `docs/rules/ai/tests.md` holds these rules.

## Non-goals

- A fake `calc_native`, in this folder or anywhere new.
- Production code: nothing under `src/` changes.
- `tests/py/ui/`: part 2, and `test_expression.py` is not touched by any part. `tests/py/unit/core`: part 3.
- `tests/py` in `make typecheck`: tests stay out of mypy, by the owner's decision.
- Tests of control: `set_theme` and menus stay in `tests/py/ui`.

## Anti-goals

- A chain test in this folder, however small it looks.
- A fake that restates the function under test.
- A framework for tests: a table is a dataclass or a `param` list, and a loop.

## What is tested, function by function

`test_typed_tables.py`, module `tcalc.typed_tables`:

- `build`: a good table; a missing key raises.
- `override`: a key applied; a bad key logged and skipped.
- `values`: all of one kind; a wrong one logged and skipped.
- `_convert_keys`, with a fake `convert`: a table; not a table; an unknown key.
- `_convert`, one row per arm on the test's own types: `NewType`, dataclass, union, tuple, enum, int for float, `Path`, scalar; a wrong type raises.
- `_enum`: by value, by name, unknown.
- `is_dataclass_type`, `_log_all`.

`test_look.py`, module `tcalc.ui.look`:

- `look_fields`, with `FakeColor`, `FakeRef` and `FakeTinted` patched over `ColorName`, `ColorRef` and `Tinted`: a color, a bare and a tinted ref, a value, a nested table.
- `qss_name`, on a dummy with a `path`.
- `Tinted`: opacity in range; above 1 raises.
- `_merged`: two tables; a table with an opacity replaced whole.
- `_hover_follows_color`: a color; an own hover.
- `with_shared_buttons`, with dummy classes patched over `KeypadLook`, `HistoryLook` and `Button`: a shared button reaches the area; an area that is not a table stays.

`test_theme.py`, module `tcalc.theme`:

- `_read`: a good file in `tmp_path`; bad toml raises `ThemeError`.
- `_folder`, `custom_theme_folders`: folders in `tmp_path`.
- `custom_themes`, with fakes for `custom_theme_folders` and `Theme`: lists names; a broken one is logged and left out.
- `_opaque`: an opaque color kept; a color with alpha logged and dropped; a gradient in `screen` kept.
- `_restored`: on the test's own dataclass.
- `ThemeChoice.scheme`, `ThemeChoice.variant`.
- `Theme.__init__`, with `_read`, `override`, `with_shared_buttons`, `_known_colors` and `_pictures` patched: a good table; no name raises; a bad base raises.
- `Theme._known_colors`, on a `Theme.__new__(Theme)` with `look_fields`, `ColorField`, `_restored` and `DEFAULT_LOOK` patched: a known color; an unknown color restored and logged.
- `Theme._pictures`, the same way, with `build` and `_folder` patched: a good entry; not a list; an entry `build` refuses.
- `Theme.qcolor`, `Theme.scheme`.
- `get_theme`, `load_theme`, with a recording class in place of `Theme`.

`test_styles.py`, module `tcalc.ui.styles`:

- `qss_color`: opaque; with an opacity.
- `apply_theme`, with a recording `app` and `load_theme`, `_build_palette`, `_app_font` and `_build_stylesheet` patched: each is applied.
- `sync_theme`, with `get_app_state`, `get_theme` and `apply_theme` patched: applies a change; does nothing when already on.

`test_ui_utils.py`, module `tcalc.ui.utils`:

- `split_camel`.
- `_apply_tint`: a tint paints the icon; `None` returns it unchanged.
- `_load_icon`, with `get_theme`, `ICONS_DIR` and `CONFIG` patched: a family file wins; an untinted icon keeps its colors.
- `get_icon`: `None` gives a null icon; a name gives an icon, with `_load_icon` patched.
- `theme_icon`: with a dummy `build`, the icon draws what `build` made.

`_apply_tint` reads its result with one pixel read of its own: a unit test imports only what it tests. `opaque_color`, the former `_opaque_color` of `test_icons.py`, moves to a new `tests/py/helpers.py` because `test_icons_on_themes.py` and `tests/py/ui/test_history.py` both read it, and one layer does not import another layer's test file.

`test_widget_utils.py`, module `tcalc.ui.widgets.utils`: `fit_radius`, `shortest_side`, `set_raised`, `apply_scaled_fonts`, each on a plain `QWidget`. The last keeps `test_a_lone_min_above_the_default_max_never_scales_backwards`.

`test_common_utils.py`, module `tcalc.ui.widgets.common.utils`: `_H_ALGN` and `_V_ALGN`, one row per arm, each arm found by `key.name`; `reposition` with fake arms and plain keys. `Align` is not imported.

`test_picture_layer.py`, module `picture_layer`: `picture_rects` and `master_size` on a dummy picture, and the `PictureLayer` tests, with a dummy `get_theme` holding one picture in place of the `sponge` fixture and `load_theme("kitty")`. The picture is an svg the test writes to `tmp_path` with `width="600" height="300"`, in place of the bundled `undersea.svg` and the svg under `ICONS_DIR`. `test_config_defaults` goes, it is a `_pictures` row now.

`test_button.py`, `test_toaster.py`: `TestOptionGroup` and `TestToaster`, split out of `test_common_widgets.py`. Each patches `get_theme` with a dummy, and a toast level is a plain string. `test_button_count`, `test_size_policy_fixed`, `test_alignment_center` and `test_word_wrap_off` only read back a constructor setting and are deleted.

`test_app_state.py`, module `tcalc.app_state`: the `AppState.theme` setting, with `custom_themes` patched and an invented theme name: `test_theme_defaults_to_system`, `test_theme_persists`, `test_bad_stored_theme_falls_back_to_system`, `test_deleted_custom_theme_falls_back_to_system`, from `test_color_scheme.py`.

`test_format_result.py`, module `tcalc.ui.controller.utils`: `format_result` on plain numbers, and on the test's own dummy types patched over `calc_native` in that module, since it branches on them: a whole `Rational`, a fraction, a `BigReal`, a `Collection`.

`tests/py/unit/ruff.toml` (new): `force-single-line`, so ruff keeps a unit test's imports one name per line. In a file that tests more than one function, each test imports its function inside its body, under the `def`. It reaches only the test files under `tests/py/unit`; in `tests/py/unit/core` it changes the import lines of `conftest.py` and `test_ops.py` and nothing else.

`test_theme_readability.py`: `test_primary_text_is_readable` and `test_control_text_is_readable_on_background` with their helpers, a separate file by the owner's decision. They read the bundled themes, since contrast on an invented theme tests nothing, and they assert a relation, not a value. They are the named exception in the rule. `place` lambdas become dotted paths. The file patches `user_themes_dir` itself, since a user theme named like a bundled one would replace it.

`conftest.py`: keeps its two environment lines. `write_theme` and `_user_themes` go, because no test left in the folder reads the user folder through them: a function that reads it gets it patched in its own test.

## What moves to `tests/py/e2e/ui/`

This folder is new here, by the owner's decision; the rest of `tests/py/ui` comes to it later (part 2). It runs as its own process. It gets a conftest with `_user_themes` and `write_theme`. These run a chain, so they move as they are, with their helpers:

- `test_styles.py`, as `test_theme_on_widgets.py`: palette roles, app font, menu and picker fonts, custom pad colors. This is what covers `_build_subs`, `_build_stylesheet` and `_build_palette`; they get no unit test, by the owner's decision.
- Into the same file: `test_every_qss_placeholder_resolves` with its `variant` rows, now derived from `BUILT_IN_VARIANTS` and the `themes` folder, and `_restore_dark`, `test_qss_names_are_unique`, `test_light_scheme_sets_light_palette` and `test_reapplying_does_not_stack_stylesheet` with the `restore` fixture, `test_theme_sets_the_monospace_font`.
- `test_format_result.py` as `test_format_result_e2e.py`: it evaluates real expressions. Its three field rows become a frozen `FormatCase`, with no comment per case.
- `test_icons.py`, all 11 tests, as `test_icons_on_themes.py`: each runs on real themes and real icon files. It keeps `_same_image` and the `light` fixture, and reads `opaque_color` from `tests/py/helpers.py`.
- `test_props.py`, with `test_only_keypad_qss_uses_keypad_colors`, which now looks for `$keypad_`: they read the stylesheet sources against seven production enums, there is no function to test.

`test_themes_and_icons_do_not_depend_on_the_working_directory` goes to its own file, `tests/py/e2e/test_working_directory.py`: it has to read the real bundled folder, which part 2 replaces in `tests/py/e2e/ui/`. It patches `user_themes_dir` itself and asserts `custom_themes()` is not empty, with no theme names.

## Deleted, because the function tests replace them

By the owner's decision, these are not moved or split row by row: `test_broken_part_falls_back`, `test_opacity_reaches_the_stylesheet`, `test_look_override_reaches_stylesheet_and_python`, `test_gradient_screen_reaches_the_stylesheet`, `test_only_primary_moves_the_hovers_and_the_selected_row`, `test_alpha_in_a_user_theme_takes_the_base_color`, `test_custom_themes_come_from_theme_files`, `test_broken_custom_theme_is_skipped`, `test_user_theme_is_listed_and_replaces_a_bundled_one`, `test_config_defaults`. The cost: no test runs a whole toml through to a stylesheet with these cases. That is e2e work for later.

## Deleted for their own reason

- `test_default_is_dark_and_unchanged`, `test_light_accent_is_orange`, `test_light_keypad_colors_are_light`, `test_new_keys_match_old_dark_values`: values of the bundled themes.
- `test_alpha_helper_is_gone`, `test_no_alpha_pairs_left_in_ui_config`: assert the absence of deleted code.
- `test_bundled_theme_colors_are_opaque`, `test_sets_have_identical_keys`, `test_builtin_themes_have_every_color_place`, `test_light_loads_only_light`, `test_base_is_the_light_or_dark_family`: read the bundled themes. `tests/py/e2e/test_bundled_themes.py`, added in part 2 by the owner's decision, is the load clean check that catches a broken bundled theme.
- `test_config_toml_builds`: `tcalc/ui/config.py` runs the same `build` call at import.
- `test_config_toml_mistake_names_its_key`: its cases are rows of `build` and `_convert_keys`.

## Done when

- `make py-lint` and `make typecheck` pass, and `make py-test` passes.
- Each function above, broken on a scratch copy of `src/`, fails its own test by name, with a sample of them shown.
- Every `unit/ui` file passes alone, and the directory passes in reverse file order.
- `grep -rnE '"(kitty|retro|sponge)"|write_theme|lambda t:' tests/py/unit/ui` finds only `test_theme_readability.py`.
- `grep -rnE '^from tcalc\.[a-z_.]+ import \(?[A-Z]' tests/py/unit/ui` finds only a class under test.
