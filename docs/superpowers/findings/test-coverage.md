# Test coverage

## 2026-10-30: functions no test reaches (#107)

Name scan on `fix/keypad-key-radius` (`327ee3a`): every Python function under `src/tcalc/` (event handlers, `__init__` and dunders left out) whose name appears nowhere under `tests/`. 610 functions, 424 never named. A name in no test is a candidate, not a proof: a nested helper is reached through its parent (`fmt_real` inside `format_result` is covered by `tests/py/unit/ui/test_format_result.py`), and a private method can run under a public one. Every item listed in #107 was checked by hand with `grep -rl <caller> tests`.

```bash
# Python: names never mentioned in tests (approximate)
.venv/bin/python - <<'EOF'
import ast, re
from pathlib import Path
tests = "\n".join(p.read_text(errors="ignore") for p in Path("tests").rglob("*.py"))
for p in sorted(Path("src/tcalc").rglob("*.py")):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.FunctionDef) and not re.search(rf"\b{re.escape(n.name)}\b", tests):
            print(p, n.name, n.lineno)
EOF
```

Modules with the most unnamed functions: `ui/widgets/keypad/custom_pad.py` 52, `ui/widgets/math/renderer/expression_node.py` 26, `ui/widgets/math/renderer/widgets.py` 25, `ui/window.py` 22, `ui/widgets/history/history.py` 21, `ui/widgets/calc/display/expression/expression.py` 18, `ui/manubar/menus/view.py` 14, `ui/widgets/math/math_primitives.py` 14.

Checked by hand, no test reaches them at all:

- Custom pad saving and loading (`CustomPad._save`, `_load`, `_load_keys`, `_resolve_key`, `KeyDef.to_settings`, `KeyDef.from_op`) and key editing (`_add_constant`, `_replace_operation`, `_remove_key`, `_recalc_positions`, `_set_key_color`).
- Keyboard input: `keymap.get_operation_for_key`, `get_expression_action_for_key`, `KeyboardHandler.handle_key_press`, `ShortcutManager`.
- Memory: `Controller.recall`, `with_value`, `Memory.set_memory`, `TopBar.set_memory_available`.
- Edit menu: history undo / redo (`_do_history_op`), `cut`, `paste`.
- `Keypad.apply_shift`, `apply_hyp_variant` / `_build_hyp_map`.
- `errors.raise_error` and the message builders in `errors.py`.
- `get_history_width_from_total`, `strip_subscript`, `space_binary_ops`.

Reached only indirectly: theme loading (`theme._read`, `custom_theme_folders`, `custom_themes`, through the bundled themes only; the #105 crash was not caught), the key fit helpers in `ui/widgets/utils.py` (pixel tests and a call count), window layout (`apply_preset_layout`, `_restore_window_state`, `_restore_custom_pads`, through `test_view_state_ui_sync.py`).

Covered although unnamed: the +/- negate (`tests/py/ui/test_expression.py`), angle units (native `test_trig.cpp`, `test_transcendental.cpp`), result formatting (`test_format_result.py`).

Native public headers (`src/native/lib/*/pub/*.hpp`) against `src/native/tests/` and `tests/py/`: `cosh`, `acosh` and `atanh` have no native test and only appear in the fake op table of `tests/py/unit/core/conftest.py`; `promote_big`, `format_expr_str` and `space_binary_op` appear in no test. The `*_scalar` statistic arms are not named, but `test_statistic.cpp` may reach them through the collection calls; not checked.
