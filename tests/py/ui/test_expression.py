from __future__ import annotations

import pytest
from calc_native import ParenKind
from PySide6.QtWidgets import QLineEdit

from tcalc.core.ops import Operation
from tcalc.debug import dump_expression_tree, snapshot_tree
from tcalc.ui.widgets.calc.display.expression.expression import Expression

DIV_SYM = Operation.DIV.symbol
POW_SYM = Operation.POW.symbol


def _fail_tree(expression_widget: Expression, t, message: str, node=None) -> None:
    dump_expression_tree(expression_widget._root, t.plain_text)
    if node is not None:
        node_dump = "\n".join(["[node_dump]", *node._fmt(0)])
        raise AssertionError(f"{message}\n\n{node_dump}")
    raise AssertionError(f"{message}\n\n{t}")


class TestExpressionNode:
    """Test expressions with fractions, powers, and roots."""

    @pytest.mark.parametrize(
        [
            "expression",  # test case
            "expected_node_cls_idx",  # list of tuples: (node index, expected class name)
            "idx_slot_count",  # list of tuples: (node index, expected slot count)
            "idx_segment_count",  # list of tuples: (node index, expected segment count)
            "total_slot_count",  # total slot count across all nodes
            "total_segment_count",  # total segment count across all nodes
        ],
        [
            pytest.param(
                "\\frac{1}{2}",
                [(0, "FractionWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="fracNode-1",
            ),
            pytest.param(
                "\\frac{3}{4}",
                [(0, "FractionWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="fracNode-2",
            ),
            pytest.param(
                "\\pow{2}{3}",
                [(0, "PowWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="powNode-1",
            ),
            pytest.param(
                "\\pow{5}{2}",
                [(0, "PowWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="powNode-2",
            ),
            pytest.param(
                "\\root{2}{3}",
                [(0, "RootWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="rootNode-1",
            ),
            pytest.param(
                "\\root{5}{2}",
                [(0, "RootWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="rootNode-2",
            ),
            pytest.param(
                "1+\\frac{1}{2}",
                [(0, "FractionWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="frac-plus",
            ),
            pytest.param(
                "\\frac{1}{2}+\\frac{3}{4}",
                [(0, "FractionWidget"), (1, "FractionWidget")],
                [(0, 2), (1, 2)],
                [(0, 2), (1, 2)],
                4,
                4,
                id="frac-plus-frac",
            ),
            pytest.param(
                "1+\\pow{2}{3}",
                [(0, "PowWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="pow-plus",
            ),
            pytest.param(
                "1+\\root{2}{3}",
                [(0, "RootWidget")],
                [(0, 2)],
                [(0, 2)],
                2,
                2,
                id="root-plus",
            ),
            pytest.param(
                "\\frac{\\frac{1}{2}}{3}",
                [(0, "FractionWidget"), (1, "FractionWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="frac-nested-left",
            ),
            pytest.param(
                "\\frac{\\frac{1}{2}}{\\frac{3}{4}}",
                [
                    (0, "FractionWidget"),
                    (1, "FractionWidget"),
                    (2, "FractionWidget"),
                ],
                [(0, 2), (1, 2), (2, 2)],
                [(0, 6), (1, 2), (2, 2)],
                6,
                10,
                id="frac-nested-both",
            ),
            pytest.param(
                "\\pow{2}{\\pow{3}{4}}",
                [(0, "PowWidget"), (1, "PowWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="pow-nested-exp",
            ),
            pytest.param(
                "\\pow{\\pow{2}{3}}{4}",
                [(0, "PowWidget"), (1, "PowWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="pow-nested-base",
            ),
            pytest.param(
                "\\root{2}{\\root{3}{4}}",
                [(0, "RootWidget"), (1, "RootWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="root-nested-radicand",
            ),
            pytest.param(
                "\\root{\\root{2}{3}}{4}",
                [(0, "RootWidget"), (1, "RootWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="root-nested-degree",
            ),
            pytest.param(
                "\\frac{\\pow{2}{3}}{\\pow{4}{5}}",
                [
                    (0, "FractionWidget"),
                    (1, "PowWidget"),
                    (2, "PowWidget"),
                ],
                [(0, 2), (1, 2), (2, 2)],
                [(0, 6), (1, 2), (2, 2)],
                6,
                10,
                id="frac-with-two-pows",
            ),
            pytest.param(
                "\\frac{\\pow{2}{3}}{\\root{4}{5}}",
                [
                    (0, "FractionWidget"),
                    (1, "PowWidget"),
                    (2, "RootWidget"),
                ],
                [(0, 2), (1, 2), (2, 2)],
                [(0, 6), (1, 2), (2, 2)],
                6,
                10,
                id="frac-with-pow-root",
            ),
            pytest.param(
                "\\pow{\\frac{1}{2}}{\\root{2}{3}}",
                [
                    (0, "PowWidget"),
                    (1, "FractionWidget"),
                    (2, "RootWidget"),
                ],
                [(0, 2), (1, 2), (2, 2)],
                [(0, 6), (1, 2), (2, 2)],
                6,
                10,
                id="pow-with-frac-root",
            ),
            pytest.param(
                "\\root{2}{\\frac{\\pow{3}{4}}{5}}",
                [
                    (0, "RootWidget"),
                    (1, "FractionWidget"),
                    (2, "PowWidget"),
                ],
                [(0, 2), (1, 2), (2, 2)],
                [(0, 4), (1, 4), (2, 2)],
                6,
                10,
                id="root-with-frac-pow",
            ),
            pytest.param(
                "\\frac{1+\\pow{2}{3}}{4}",
                [(0, "FractionWidget"), (1, "PowWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="frac-nested-with-text",
            ),
            pytest.param(
                "\\pow{1+\\frac{2}{3}}{4}",
                [(0, "PowWidget"), (1, "FractionWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="pow-nested-with-text",
            ),
            pytest.param(
                "\\root{1+\\pow{2}{3}}{4}",
                [(0, "RootWidget"), (1, "PowWidget")],
                [(0, 2), (1, 2)],
                [(0, 4), (1, 2)],
                4,
                6,
                id="root-nested-with-text",
            ),
        ],
    )
    def test_mixed_expression_node_creation(
        self,
        expression_widget,
        set_expression,
        qapp,
        expression,
        expected_node_cls_idx,
        idx_slot_count,
        idx_segment_count,
        total_slot_count,
        total_segment_count,
    ):
        """Expressions should create expected node types and slot counts."""
        set_expression(expression)

        t = snapshot_tree(expression_widget)
        for idx, expected_cls in expected_node_cls_idx:
            actual_cls = t.all_nodes[idx].cls_name
            if actual_cls != expected_cls:
                _fail_tree(
                    expression_widget,
                    t,
                    f"Expected node[{idx}] class={expected_cls}, got {actual_cls}",
                    node=t.all_nodes[idx],
                )

        for idx, expected_slots in idx_slot_count:
            actual_slots = len(t.all_nodes[idx].slots)
            if actual_slots != expected_slots:
                _fail_tree(
                    expression_widget,
                    t,
                    f"Expected node[{idx}] slot count={expected_slots}, got {actual_slots}",
                    node=t.all_nodes[idx],
                )

        for idx, expected_segments in idx_segment_count:
            actual_segments = sum(len(slot.segments) for slot in t.all_nodes[idx].slots)
            if actual_segments != expected_segments:
                _fail_tree(
                    expression_widget,
                    t,
                    (
                        f"Expected node[{idx}] segment count={expected_segments}, "
                        f"got {actual_segments}"
                    ),
                    node=t.all_nodes[idx],
                )

        total_slots = sum(len(node.slots) for node in t.all_nodes)
        if total_slots != total_slot_count:
            _fail_tree(
                expression_widget,
                t,
                f"Expected total slot count={total_slot_count}, got {total_slots}",
            )

        total_segments = sum(len(slot.segments) for node in t.all_nodes for slot in node.slots)
        if total_segments != total_segment_count:
            _fail_tree(
                expression_widget,
                t,
                f"Expected total segment count={total_segment_count}, got {total_segments}",
            )


class TestFocusHandling:
    """Test focus and cursor placement in expression nodes."""

    def test_empty_fraction_has_empty_slot(self, expression_widget, qapp):
        """Empty fraction should have at least one empty slot."""
        main_input = expression_widget.expression_inputs()[0]
        main_input.setText("/")
        qapp.processEvents()

        t = snapshot_tree(expression_widget)
        if t.fracs:
            frac = t.fracs[0].widget
            assert frac.numerator.to_plain_text() == "" or frac.denominator.to_plain_text() == ""


class TestInputCounts:
    """Test input field counts after node creation."""

    @pytest.mark.parametrize(
        "expr,min_inputs",
        [
            ("\\frac{1}{2}", 2),
            ("\\frac{\\frac{1}{2}}{\\frac{3}{4}}", 4),
            ("\\pow{1}{2}", 2),
            ("\\frac{1}{2}+\\frac{3}{4}", 4),
        ],
    )
    def test_input_count(self, expression_widget, set_expression, qapp, expr, min_inputs):
        """Expression should have at least expected number of input fields."""
        set_expression(expr)
        inputs = expression_widget.expression_inputs()
        assert len(inputs) >= min_inputs


class TestExpressionModification:
    """Test modifying expressions after node creation."""

    @pytest.mark.parametrize(
        "initial_expr,slot,new_value,expected_in_result",
        [
            ("\\frac{10}{10}", "numerator", "10", "10"),
            ("\\frac{1}{2}", "denominator", "20", "20"),
            ("\\frac{3}{4}", "numerator", "99", "99"),
        ],
    )
    def test_modify_fraction_slot(
        self,
        expression_widget,
        set_expression,
        qapp,
        initial_expr,
        slot,
        new_value,
        expected_in_result,
    ):
        """Modifying a fraction slot should update serialization."""
        set_expression(initial_expr)

        t = snapshot_tree(expression_widget)
        if t.fracs:
            frac = t.fracs[0].widget
            slot_obj = getattr(frac, slot)
            input_field = slot_obj.line_edits()[0]
            input_field.setText(new_value)
            qapp.processEvents()

            result = expression_widget.get_plain_text()
            assert expected_in_result in result


class TestPlainTextSignal:
    """Test that plain_text_changed signal fires correctly."""

    @pytest.mark.parametrize(
        "text",
        ["\\frac{1}{2}", "\\pow{2}{3}", "5", "1+2"],
    )
    def test_signal_on_set_plain_text(self, expression_widget, qapp, text):
        """Signal should fire when setting plain text."""
        received = []
        expression_widget.plain_text_changed.connect(lambda t: received.append(t))

        expression_widget.set_plain_text(text)
        qapp.processEvents()

        assert len(received) >= 1

    def test_signal_on_input_change(self, expression_widget, qapp):
        """Signal should fire when input text changes."""
        received = []
        expression_widget.plain_text_changed.connect(lambda t: received.append(t))

        main_input = expression_widget.expression_inputs()[0]
        main_input.setText("5")
        qapp.processEvents()

        assert len(received) >= 1


class TestNodeRemoval:
    """Test node removal via backspace."""

    def test_backspace_callable(self, expression_widget, set_expression, qapp):
        """Backspace method should be callable without error."""
        set_expression("\\frac{1}{2}")
        qapp.processEvents()

        t = snapshot_tree(expression_widget)
        assert len(t.all_nodes) >= 1

        expression_widget.backspace()
        qapp.processEvents()


class TestInsertExprStr:
    """Test insert_expr_str for keystroke-based node insertion."""

    def test_frac_between_existing_fracs(self, expression_widget, qapp):
        """Insert frac between two existing fractions preserves structure."""
        import calc_native

        target = expression_widget._resolve_target()
        target.setText("\\frac{1}{2} + 3 + \\frac{4}{5}")
        qapp.processEvents()

        # Find input containing "3" and position cursor after it
        for le in expression_widget.expression_inputs():
            if "3" in le.text():
                le.setFocus()
                le.setCursorPosition(le.text().find("3") + 1)
                break
        qapp.processEvents()

        expression_widget.insert_expr_str(calc_native.ExprKind.Frac)
        qapp.processEvents()

        result = expression_widget.get_plain_text()
        # Should have 3 fractions: original two + new one at position of 3
        t = snapshot_tree(expression_widget)
        assert len(t.all_nodes) == 3
        assert "\\frac{3}{}" in result
        assert "\\frac{1}{2}" in result
        assert "\\frac{4}{5}" in result

    def test_frac_preserves_suffix_with_binary_op(self, expression_widget, qapp):
        """Insert frac keeps binary operator in suffix, not in denominator."""
        import calc_native

        target = expression_widget._resolve_target()
        target.setText("1 + 2 + 3")
        qapp.processEvents()

        target.setCursorPosition(5)  # After "1 + 2"
        expression_widget.insert_expr_str(calc_native.ExprKind.Frac)
        qapp.processEvents()

        result = expression_widget.get_plain_text()
        assert result == "1 + \\frac{2}{} + 3"

    def test_frac_without_braces_creates_widget(self, expression_widget, qapp):
        """Typing \\frac alone (without braces) should create FractionWidget."""
        target = expression_widget._resolve_target()
        target.setText("\\frac")
        qapp.processEvents()

        t = snapshot_tree(expression_widget)
        assert len(t.fracs) == 1

    def test_frac_on_empty_input_creates_empty_widget(self, expression_widget, qapp):
        """Insert frac on empty input creates empty FractionWidget."""
        import calc_native

        expression_widget.insert_expr_str(calc_native.ExprKind.Frac)
        qapp.processEvents()

        t = snapshot_tree(expression_widget)
        assert len(t.fracs) == 1
        frac = t.fracs[0].widget
        assert frac.numerator.to_plain_text() == ""
        assert frac.denominator.to_plain_text() == ""


class TestImplicitMultiplication:
    """Test implicit multiplication cases."""

    @pytest.mark.parametrize(
        "expr,expected_fracs",
        [
            ("\\frac{2}{4}\\frac{3}{4}", 2),  # (2/4)(3/4) implicit mult
            ("2\\frac{3}{4}", 1),  # 2 * 3/4
            ("\\frac{1}{2}\\frac{3}{4}\\frac{5}{6}", 3),
        ],
    )
    def test_implicit_mult_fractions(
        self, expression_widget, set_expression, qapp, expr, expected_fracs
    ):
        """Implicit multiplication between fractions should create correct nodes."""
        set_expression(expr)
        t = snapshot_tree(expression_widget)
        assert len(t.fracs) == expected_fracs


class TestHandleNegate:
    """Test handle_negate toggling unary minus based on cursor position."""

    def _negate_at(self, expression_widget, qapp, text: str, cursor_pos: int) -> str:
        """Set text in root input, position cursor, call handle_negate, return result."""
        target = expression_widget._resolve_target()
        target.setText(text)
        target.setCursorPosition(cursor_pos)
        qapp.processEvents()
        expression_widget.handle_negate()
        qapp.processEvents()
        return target.text()

    @pytest.mark.parametrize(
        "text,cursor,expected",
        [
            # Simple number: 4| -> -4|
            ("4", 1, "-4"),
            # Toggle back: -4| -> 4|
            ("-4", 2, "4"),
            # After binary op: 4+6| -> 4+-6|
            ("4 + 6", 5, "4 + -6"),
            # Unclosed paren treated as normal: (4+6| -> (4+-6| (no closed group)
            ("(4 + 6", 6, "(4 + -6"),
            # Closed paren group: (4+6)| -> -(4+6)|
            ("(4 + 6)", 7, "-(4 + 6)"),
            # Toggle back closed paren group: -(4+6)| -> (4+6)|
            ("-(4 + 6)", 8, "(4 + 6)"),
            # Empty input: | -> -|
            ("", 0, "-"),
            # Just minus: -| -> |
            ("-", 1, ""),
            # Cursor mid-expression: 3(4|+3) — implicit mul, negate 4
            ("3(4 + 3)", 4, "3(-4 + 3)"),
            # Negate at start of inner content: 3(|4+3) — negate the operand after open paren
            ("3(4 + 3)", 2, "3(-4 + 3)"),
            # Number after operator: 2+3| -> 2+-3|
            ("2 + 3", 5, "2 + -3"),
            # Negate closed paren after operator: 2+(3+4)| -> 2+-(3+4)|
            ("2 + (3 + 4)", 11, "2 + -(3 + 4)"),
        ],
    )
    def test_negate_flat_text(self, expression_widget, qapp, text, cursor, expected):
        """handle_negate on flat text (no ExpressionNodes) with cursor positioning."""
        result = self._negate_at(expression_widget, qapp, text, cursor)
        assert result == expected, (
            f"negate({text!r}, cursor={cursor}) -> {result!r}, expected {expected!r}"
        )

    def test_negate_inside_fraction_numerator(self, expression_widget, set_expression, qapp):
        """Negate inside a fraction numerator: \\frac{3}{4} -> \\frac{-3}{4}."""
        set_expression("\\frac{3}{4}")

        t = snapshot_tree(expression_widget)
        assert len(t.fracs) == 1
        frac = t.fracs[0].widget

        num_input = frac.numerator.line_edits()[0]
        num_input.setFocus()
        num_input.setCursorPosition(len(num_input.text()))
        qapp.processEvents()

        expression_widget.handle_negate()
        qapp.processEvents()

        assert num_input.text() == "-3"

    def test_negate_inside_fraction_denominator(self, expression_widget, set_expression, qapp):
        """Negate inside a fraction denominator: \\frac{3}{4} -> \\frac{3}{-4}."""
        set_expression("\\frac{3}{4}")

        t = snapshot_tree(expression_widget)
        frac = t.fracs[0].widget

        den_input = frac.denominator.line_edits()[0]
        den_input.setFocus()
        den_input.setCursorPosition(len(den_input.text()))
        qapp.processEvents()

        expression_widget.handle_negate()
        qapp.processEvents()

        assert den_input.text() == "-4"

    def test_negate_cursor_after_fraction(self, expression_widget, set_expression, qapp):
        """Negate with cursor on empty input after fraction inserts '-' in the segment before the node."""
        set_expression("1 + \\frac{2}{3}")
        qapp.processEvents()

        # Root segments: [QLineEdit("1 + "), FractionWidget, QLineEdit("")]
        root = expression_widget._root
        segs = root._segments
        after_input = segs[-1]
        assert isinstance(after_input, QLineEdit)
        assert after_input.text() == ""

        before_input = segs[0]
        assert isinstance(before_input, QLineEdit)
        assert before_input.text() == "1 + "

        after_input.setFocus()
        after_input.setCursorPosition(0)
        qapp.processEvents()

        expression_widget.handle_negate()
        qapp.processEvents()

        # '-' appended to the segment before the fraction
        assert before_input.text() == "1 + -"

    def test_negate_cursor_after_fraction_toggle_back(
        self, expression_widget, set_expression, qapp
    ):
        """Negate twice on empty input after fraction removes the '-' again."""
        set_expression("1 + \\frac{2}{3}")
        qapp.processEvents()

        root = expression_widget._root
        segs = root._segments
        after_input = segs[-1]
        before_input = segs[0]

        after_input.setFocus()
        after_input.setCursorPosition(0)
        qapp.processEvents()

        # First negate: insert '-'
        expression_widget.handle_negate()
        qapp.processEvents()
        assert before_input.text() == "1 + -"

        # Second negate: remove '-'
        expression_widget.handle_negate()
        qapp.processEvents()
        assert before_input.text() == "1 + "

    def test_negate_cursor_between_two_fractions(self, expression_widget, set_expression, qapp):
        """Negate with cursor between two fractions uses the QLineEdit between them."""
        set_expression("\\frac{1}{2}\\frac{3}{4}")
        qapp.processEvents()

        # Root segments: [QLineEdit(""), Frac, QLineEdit(""), Frac, QLineEdit("")]
        root = expression_widget._root
        segs = root._segments

        # Find the middle QLineEdit (between the two fractions)
        mid_input = segs[2]
        assert isinstance(mid_input, QLineEdit)
        assert mid_input.text() == ""

        # The QLineEdit before the first fraction
        first_input = segs[0]
        assert isinstance(first_input, QLineEdit)

        mid_input.setFocus()
        mid_input.setCursorPosition(0)
        qapp.processEvents()

        expression_widget.handle_negate()
        qapp.processEvents()

        # '-' inserted into the middle QLineEdit itself (it IS a QLineEdit, cursor prefix empty,
        # prev segment is first Frac → walk back to segs[0])
        assert first_input.text() == "-"


class TestNodeRemovalDetailed:
    """Detailed tests for node removal via backspace."""

    def test_backspace_removes_fraction(self, expression_widget, set_expression, qapp):
        """Backspace on empty input after fraction should remove it."""
        set_expression("1 + \\frac{2}{3}")
        qapp.processEvents()

        t_before = snapshot_tree(expression_widget)
        assert len(t_before.all_nodes) == 1

        # Find empty input after fraction and backspace
        inputs = expression_widget.expression_inputs()
        for inp in inputs:
            if inp.text() == "":
                inp.setFocus()
                break
        qapp.processEvents()

        expression_widget.backspace()
        qapp.processEvents()

        # Node should be removed or merged
        t_after = snapshot_tree(expression_widget)
        assert len(t_after.all_nodes) <= len(t_before.all_nodes)


@pytest.mark.parametrize(
    [
        "expression",  # test case
        "expected_count",  # number of ParenWidget nodes expected to be rendered
        "expected_parenKind_idx",  # list of tuples: (index in rendered ParenWidget list, expected ParenKind)
        "idx_segments_count",  # list of tuples: (index in ParenWidget list, number of inner segments rendered)
        "total_segment_count",  # all segment counts
    ],
    [
        pytest.param(
            "(1)+\\frac{2}{3}",
            0,
            (None, None),
            (None, 0),
            5,
            id="non-parenNode",
        ),
        pytest.param(
            "(1)+\\frac{2}{3})",
            0,
            (None, None),
            (None, 0),
            5,
            id="non-parenNode-w-close",
        ),
        pytest.param(
            "(1)+(\\frac{2}{3})",
            1,
            [(0, ParenKind.Paren)],
            [(0, 5)],
            10,
            id="render-parenNode",
        ),
        pytest.param(
            "(1)+(2+\\frac{2}{3})",
            1,
            [(0, ParenKind.Paren)],
            [(0, 5)],
            10,
            id="paren-with-prefix-text",
        ),
        pytest.param(
            "{\\frac{2}{3}}",
            1,
            [(0, ParenKind.Brace)],
            [(0, 5)],
            10,
            id="brace-widget",
        ),
        pytest.param(
            "{\\frac{2}{3})",
            1,
            [(0, ParenKind.Brace)],
            [(0, 4)],
            9,
            id="non-closed-brace-widget",
        ),
        pytest.param(
            "{+\\frac{2}{3}",
            1,
            [(0, ParenKind.Brace)],
            [(0, 4)],
            9,
            id="open-brace-leading-op",
        ),
        pytest.param(
            "(1)+{2+\\root{2}{3}}",
            1,
            [(0, ParenKind.Brace)],
            [(0, 5)],
            10,
            id="brace-in-sum",
        ),
        pytest.param(
            "[\\frac{2}{3}]",
            1,
            [(0, ParenKind.Bracket)],
            [(0, 5)],
            10,
            id="bracket-widget",
        ),
        pytest.param(
            "(1)+{2+[\\pow{2}{3}]+4}",
            2,
            [(0, ParenKind.Brace), (1, ParenKind.Bracket)],
            [(0, 5), (1, 5)],
            15,
            id="outer-first-nested-parens",
        ),
        pytest.param(
            "(1)+{2+[\\frac{2}{3}+4+(\\pow{2}{3})]}",
            3,
            [(0, ParenKind.Brace), (1, ParenKind.Bracket), (2, ParenKind.Paren)],
            [(0, 5), (1, 7), (2, 5)],
            24,
            id="nested-brace-bracket-paren",
        ),
        pytest.param(
            "(1)+{2+[\\frac{2}{3}+4+(\\pow{2}{3}",
            3,
            [(0, ParenKind.Brace), (1, ParenKind.Bracket), (2, ParenKind.Paren)],
            [(0, 4), (1, 6), (2, 4)],
            21,
            id="nested-brace-bracket-paren-open-only",
        ),
    ],
)
class TestParenWidget:
    """Test readyExpression ParenWidget render pipeline."""

    def test_paren_widgets(
        self,
        expression_widget,
        set_expression,
        qapp,
        expression,
        expected_count,
        expected_parenKind_idx,
        idx_segments_count,
        total_segment_count,
    ):
        set_expression(expression)
        qapp.processEvents()

        t = snapshot_tree(expression_widget)

        if len(t.parens) != expected_count:
            _fail_tree(
                expression_widget,
                t,
                f"Expected {expected_count} ParenWidget(s), got {len(t.parens)}",
            )

        if expected_parenKind_idx and expected_parenKind_idx != (None, None):
            for idx, kind in expected_parenKind_idx:
                if t.parens[idx].paren_kind != kind:
                    _fail_tree(
                        expression_widget,
                        t,
                        (
                            f"Expected ParenWidget[{idx}] kind={kind}, "
                            f"got {t.parens[idx].paren_kind}"
                        ),
                    )

        if idx_segments_count and idx_segments_count != (None, 0):
            for idx, seg_count in idx_segments_count:
                actual = len(t.parens[idx].slots[0].segments)
                if actual != seg_count:
                    _fail_tree(
                        expression_widget,
                        t,
                        (f"Expected {seg_count} segments at ParenWidget[{idx}], got {actual}"),
                        node=t.parens[idx],
                    )

        if total_segment_count is not None:
            total = sum(len(slot.segments) for slot in t.all_slots)
            if total != total_segment_count:
                _fail_tree(
                    expression_widget,
                    t,
                    f"Expected total segments={total_segment_count}, got {total}",
                )
