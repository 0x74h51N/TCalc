# Expression editor

The math-mode expression editor: how a key becomes text, Math Widgets and a plain text row, how the cursor moves, and how Math Widgets are taken apart again. The editor is `Expression` (`src/tcalc/ui/widgets/calc/display/expression/expression.py`); its widgets and the renderer are in `src/tcalc/ui/widgets/math/renderer/`. How the tokens become math nodes is in [parser.md](parser.md#build_math_nodes-render-tree), and [data-flow.md](data-flow.md) traces three expressions through both the eval path and this render path. The terms (slot, field, segment, prefix, suffix, Math Widget, dissolve...) are defined in the [glossary](glossary.md).

## Parts

- `Expression` holds the main slot (`_root`, an `ExpressionSlot` of kind main), its own `MathRender`, the last focused field (`_last_focused`) and the pending parens (`_pending_parens`). It decides which field a key goes to (`_resolve_target`: the focused field, else the last focused one, else the main slot's last field) and emits `plain_text_changed` with the whole row.
- `MathRender` (`math_render.py`) builds Math Widgets from the tokens of one field. The result display has its own read-only `MathRender` and slot (`result.py`).
- `ExpressionSlot` and `ExpressionNode` (`expression_node.py`) are the slot and the base of every Math Widget. The Math Widgets are in `widgets.py`: `FractionWidget`, `PowWidget` and `SubWidget` (both `ScriptNode`), the sqrt Math Widget, and the `ParenWidget` kinds.
- `Display` (`display.py`) forwards `plain_text_changed` as `expression_changed`, which the controller evaluates for the live result, and refits the fonts.

## From a key to the editor

`KeyboardHandler` (`ui/keyboard/handler.py`) puts an event filter on every field; the editor's `input_created` signal, emitted when a slot registers a new field, keeps that list complete. Left, Right, Up and Down call `navigate_*` directly (`EXPRESSION_KEY_MAP`). Every other mapped key clicks its keypad button, or calls the controller's handler when no button shows it, so a typed key and a clicked key take the same path.

The controller then calls one of the editor's entry points:

- `insert_text` puts text at the cursor of the target field; `apply_key` does the same for an operator, adding the spaces of a binary operator or the open paren of a unary function.
- `insert_expr_str` writes the empty LaTeX of a LaTeX expression (`\frac{}{}`, from `format_expr_str`) at the cursor. The render path below turns it into a Math Widget, so a key never builds a widget by hand.
- `backspace`, `handle_negate` and `set_plain_text`, below.

## From a field's text to Math Widgets

Each field's `textChanged` calls `_on_input_changed`, which remembers the field and schedules `_flush_exp_nodes` for the next event loop turn; changes made while the renderer is working (`is_rendering`) are ignored. `_flush_exp_nodes` runs `_add_exp_node` on the field, then emits `plain_text_changed`.

`_add_exp_node` tokenizes only that field's text and picks one path:

- Without LaTeX, a close paren that matches a pending paren closes it (`_try_close_paren`), an open paren with Math Widgets to its right wraps them (`_try_open_paren`), and anything else only has its aliases rewritten as symbols (`normalize_text`).
- With LaTeX, `MathRender.render_node` builds the math nodes (`build_math_nodes`) and `_render_row` walks them. The field is emptied and takes the first text node. Each LaTeX or paren node becomes its Math Widget, the same walk fills its slots, and it goes into the slot right after the current field with a new field after it, its suffix, which takes the next text node. At the end the new Math Widget takes the focus (`focus_default`: an empty left slot first, else the right slot) and every touched field is refitted to its text.

## Layout rules

A slot starts with a field (`ExpressionSlot.__init__`; a paren's inner slot starts with its open glyph, then the field), and every Math Widget gets a suffix (`MathRender._render_row`, `MathRender.insert_node`). Between two Math Widgets there is exactly one field: the suffix of the first is the prefix of the second. `2 + \frac{3}{4} + 5` is the main slot `'2 + '`, `FractionWidget`, `' + 5'`; turning `5` into a `FractionWidget` gives `'2 + '`, `FractionWidget`, `' + '`, `FractionWidget`, `''`, with `' + '` shared.

A closed `ParenWidget` follows the same rule on both levels. Its inner slot holds the glyphs as segments around its own row, and the `ParenWidget` gets a suffix in its parent slot. `3 + (\frac{5}{6})` is the main slot `'3 + '`, `RoundParenWidget`, `''`, and the inner slot is the open glyph, `''`, `FractionWidget`, `''`, the close glyph: the field before the close glyph is the `FractionWidget`'s suffix, the field after the `RoundParenWidget` is its own suffix.

The exception is an unclosed `ParenWidget`: it gets no suffix, because the rest of the row goes into its inner slot so the cursor stays inside the open paren. A slot can therefore end with an unclosed `ParenWidget` instead of a field, and its last field is inside that paren (`line_edits()[-1]`).

## Pending parens

An open paren with no close yet is a pending paren: an unclosed `ParenWidget`, kept on a stack per paren kind (`_pending_parens`, shared with the renderer).

- An open paren typed in a field that has Math Widgets to its right (`_try_open_paren`) cuts the slot after the field (`detach_right_of`), creates the unclosed `ParenWidget` with the text after the paren in its inner slot, moves the cut segments into it (`adopt_segments`) and puts the cursor at the start of the inner slot.
- A close paren typed in the inner slot of the pending paren of its kind (`_try_close_paren`) closes it (`set_close`). The text before the close stays in the inner slot; the text after it and any Math Widgets after it go to the `ParenWidget`'s suffix, where the cursor goes. A closed paren that holds no Math Widget is dissolved back into text.
- Backspace on a glyph removes that glyph (`ParenWidget.remove`). With the open glyph gone the `ParenWidget` dissolves; with only the close glyph gone it takes the segments after it inside and becomes pending again.

## Cursor movement

- Left and Right move inside a field until its first or last index. There, `_iter_line_edits` gives the next field in the slot, entering a Math Widget through its left slot's fields (`_direct_edits[-1]` from the right, `[0]` from the left); at the end of a slot it climbs to the slot around the Math Widget.
- Up and Down move between the top slot and the bottom slot of the nearest Math Widget that has them (`slot_above`, `slot_below`), climbing outwards until one does, then descend through the first Math Widget of the slot they enter. In a `FractionWidget` the cursor keeps its index; elsewhere it goes to the end of the field.
- Backspace right after a spaced operator removes the operator and its spaces together. At the first index of a field it acts on the segment before it: a Math Widget is entered at its last field (`line_edits()[-1]`), a glyph is removed, a field loses its last character. In an empty right slot it dissolves the Math Widget.

Where each Math Widget is entered today, measured, and where it should be, decided in #219, are in [the dissolve and cursor findings](superpowers/findings/editor-dissolve-cursor.md).

## Dissolve

Three paths call `dissolve()`:

- Backspace in an empty right slot (`Expression.backspace`): a `FractionWidget`, `PowWidget`, `SubWidget` or the sqrt Math Widget dissolves.
- Backspace on the open glyph of a `ParenWidget` (`ParenWidget.remove`, then `_dissolve`).
- A typed close paren that leaves its pending `ParenWidget` with no Math Widget inside (`Expression._try_close_paren`).

With no Math Widget in the left slot, the left slot's text is written into the parent's field at the cursor. With a Math Widget there, the left slot's segments move into the parent slot (`ExpressionSlot.replace_with`, `_splice`), and the fields that meet merge: the parent's prefix with the first moved field, and the last moved field with the parent's suffix, which merges into it.

Then the cascade: a `ParenWidget` around the cursor that no longer holds a Math Widget dissolves into text too, outwards until one does.

This is the behavior on master today. #219 changes where Left, Right and Backspace enter a Math Widget and lets Backspace dissolve a `FractionWidget` or the sqrt Math Widget from the first index of either slot.

## Negate

`handle_negate` toggles a unary minus on the operand before the cursor: it tokenizes the text before the cursor, finds its last operand (`split_operand`) and adds or removes the minus in front of it. Inside an unclosed paren it works on the paren's content. With no operand before the cursor it toggles the minus at the start of the text after it, and at the first index of a field it toggles a minus at the end of the field before it in the slot.

## Plain text

`get_plain_text` is the main slot's `to_plain_text`: fields give their text, a Math Widget gives its LaTeX (`format_expr_str` with its two slots), and an inner slot adds its paren symbols. `set_plain_text` (history, undo and redo, paste) empties the main slot and writes the whole text into its one field; the normal render path then rebuilds every Math Widget.

## Sizes and alignment

`update_input_fonts` fits every field's font to the display, a script slot's fields smaller the deeper they sit (`SCRIPT_SCALES`), and every field's width follows its text (`update_autowidth`). Each slot lines its segments up on its anchor through the margin update, which runs after a change or a resize and climbs to the main slot.

## Tests

`tests/py/e2e/ui/test_expression.py` drives a real `Expression` through tables: `EXPRESSION_NODE_CASES` (rendering), `NODE_INSERT_CASES`, `NODE_BACKSPACE_CASES`, `NAV_CASES`, `MARGIN_ALIGN_CASES` and `SCRIPT_SQUEEZE_CASES`. A case names a field by path: `("root", i)` is segment `i` of the main slot, `("node", n, slot, i)` is field `i` of slot `slot` of Math Widget `n`, counted in the order the debug tree dump walks them. A failing case logs the debug tree dump.
