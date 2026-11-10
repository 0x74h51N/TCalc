# Editor dissolve and cursor (#184, #219)

Terms as in [editor.md](../../editor.md).

## 2026-11-10: the dissolve cursor bug is not sqrt specific (master f465285)

Backspace in an empty right slot (`Expression.backspace` calls `ExpressionNode.dissolve()`) puts the cursor in the wrong place for every Math Widget whose left slot holds another Math Widget: `FractionWidget` (empty denominator), `PowWidget` (empty exponent), the sqrt Math Widget (empty degree). With only text in the left slot, the cursor lands after the moved content.

Probe (`Expression` widget offscreen, cursor at the first index of the outer Math Widget's right slot, one `backspace()`), the field and cursor after:

- `2 + \root{\frac{4}{5}}{}`, `2 + \frac{\frac{4}{5}}{}`, `2 + \root{\root{4}{2}}{}`, `2 + \frac{\root{4}{2}}{}`, `2 + \frac{4}{5}^{}`, `2 + \root{4}{2}^{}`: `'2 + '` cursor 4, before the moved Math Widget.
- `2 + \frac{1 + \frac{4}{5}}{}`: `'2 + 1 + '` cursor 4, before even the moved text `1 + `.
- `2 + \frac{\frac{4}{5} + 1}{}`: `'2 + '` cursor 4, not after ` + 1`.
- `\root{\frac{4}{5}}{} + 1`: `''` cursor 0.
- `2 + \root{\frac{\frac{4}{5}}{}}{3}`, the inner `FractionWidget` dissolving inside a sqrt Math Widget with a filled degree: the cursor lands before the moved `FractionWidget`, so the outer Math Widget does not matter.
- `2 + \root{(\frac{4}{5} + 1}{}`: the radicand ends with an unclosed `ParenWidget`, which has no suffix; the cursor lands at `'2 + |'`.
- Empty fields around the Math Widget do not matter: `2 + \frac{1 + \frac{4}{5} + 1}{} + 3` lands at `'2 + |1 + '`.

Cause: the two branches of `ExpressionNode.dissolve()` place the cursor differently. Without a Math Widget in the left slot, `_write_back_at_cursor(focus, plain, len(plain))` puts it after the content. With one, the cursor is whatever `ExpressionSlot.replace_with` returns from `_splice`, which focuses the left merge point: where the dissolved Math Widget started.

## 2026-11-10: failed attempt, focus the right merge point in `_splice`

Changed `_splice` to focus the right merge point (the end of the spliced content) when one happens. The super sexy mighty overthinked case tables of `tests/py/e2e/ui/test_expression.py` caught it: four `ParenWidget` rows of `NODE_BACKSPACE_CASES` turned red (`dissolve-paren-w-remove-only-open`, `dissolve-outer-paren-w-remove-only-open`, `dissolve-list-w-remove-open`, `dissolve-point-w-remove-open`): Backspace on an open glyph also reaches `_splice` (`ParenWidget.remove`, `_dissolve`, `ExpressionNode.dissolve`) and must leave the cursor at the start, where the open glyph was. `_splice` cannot tell the two cases apart; where the cursor lands belongs to the caller of `dissolve()`. Reverted.

## 2026-11-10: where Left, Right and Backspace move the cursor today (master f465285)

Backspace from a Math Widget's suffix enters `prev.line_edits()[-1]` (`Expression.backspace`), the last field in LaTeX text order. Left from the suffix enters `_left_slot._direct_edits[-1]` (`Expression._iter_line_edits`); Right from the prefix enters `_left_slot._direct_edits[0]`. Leaving a slot at its first or last index with Left or Right goes to the Math Widget's prefix or suffix, never to its other slot.

Measured on `2 + <Math Widget> + 5`:

- `FractionWidget`: Left from the suffix enters the last index of the numerator, Backspace the last index of the denominator. Left at the first index of the denominator goes to the prefix, Right at its last index to the suffix.
- `PowWidget`: Left from the suffix enters the last index of the base, skipping the exponent; Backspace enters the last index of the exponent. Left at the first index of the exponent goes to the prefix; Right at the last index of the base goes to the suffix.
- sqrt Math Widget: Left from the suffix enters the last index of the radicand; Backspace enters the last index of the degree. Left at the first index of the degree goes to the prefix; Right at its last index goes to the suffix.
- `SubWidget`: Left from the suffix enters the last index of the base, Backspace the last index of the subscript; Backspace at the first index of the base does nothing.
- Backspace at the first index of a left slot (numerator, base, radicand), empty or not, does nothing; at the first index of a filled right slot it does nothing either.

## 2026-11-10: the behavior wanted, decided by the human agent

The full list, with ticks for what already works, is #219. In short:

- Backspace from the suffix enters the last index of the denominator (`FractionWidget`), the exponent (`PowWidget`), the radicand (sqrt Math Widget). Left from the suffix enters the last index of the numerator, the exponent, the radicand.
- The slots of one Math Widget are visited in drawing order: `PowWidget` base then exponent, sqrt degree then radicand. `FractionWidget` stays as it is.
- `FractionWidget` and sqrt dissolve with Backspace at the first index of either slot, empty or not. The contents stay side by side in drawing order and the cursor stays where it was: `\frac{2}{3}` gives `2|3` from the denominator, `|23` from the numerator, `2|` and `|3` when the slot is empty; `\sqrt[2]{3}` gives `2|3` from the radicand, `2|` with an empty radicand, `|23` from the degree, `|3` with an empty degree.
- `PowWidget` and `SubWidget` never dissolve from the base. `SubWidget` takes a single character by design, is right today and stays as it is. `ParenWidget` is right today, its dissolve included; its xfail rows come after #219.
- Up and Down are right today.

So an empty degree puts the cursor before the radicand, and the first steps of #184 no longer show a bug; #184 is reproduced again on top of #219, with a `FractionWidget` example.

Seen in the code, no failing input found yet: Left and Right enter a slot through `_direct_edits[-1]` and `[0]`, and `_direct_edits` keeps fields in creation order (`insert_input` appends), not in the order they sit in the slot.
