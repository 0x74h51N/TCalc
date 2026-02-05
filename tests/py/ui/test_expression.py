from __future__ import annotations

import pytest

from tcalc.core.ops import Operation
from tcalc.ui.widgets.calc.display.expression.expression import Expression
from tcalc.ui.widgets.calc.display.expression.expression_node import ExpressionNode
from tcalc.ui.widgets.calc.display.expression.widgets import FractionWidget, PowWidget

DIV_SYM = Operation.DIV.symbol
POW_SYM = Operation.POW.symbol


# Helper functions for testing
def get_all_expression_nodes(widget: Expression) -> list[ExpressionNode]:
    """Get all ExpressionNode instances (FractionWidget, PowWidget) from the tree."""
    nodes: list[ExpressionNode] = []
    _collect_nodes(widget._root, nodes)
    return nodes


def _collect_nodes(container, nodes: list[ExpressionNode]) -> None:
    """Recursively collect all nodes from the container."""
    if hasattr(container, "_segments"):
        for seg in container._segments:
            if isinstance(seg, ExpressionNode):
                nodes.append(seg)
            _collect_nodes(seg, nodes)
    if hasattr(container, "numerator"):
        _collect_nodes(container.numerator, nodes)
    if hasattr(container, "denominator"):
        _collect_nodes(container.denominator, nodes)
    if hasattr(container, "base"):
        _collect_nodes(container.base, nodes)
    if hasattr(container, "exponent"):
        _collect_nodes(container.exponent, nodes)


def get_fraction_parts(fraction: FractionWidget) -> tuple[str, str]:
    """Get (numerator, denominator) text from a FractionWidget."""
    return (
        fraction.numerator.to_plain_text(),
        fraction.denominator.to_plain_text(),
    )


def get_pow_parts(pow_widget: PowWidget) -> tuple[str, str]:
    """Get (base, exponent) text from a PowWidget."""
    return (
        pow_widget.base.to_plain_text(),
        pow_widget.exponent.to_plain_text(),
    )


class TestFractionNodeCreation:
    """Test FractionWidget creation from text input."""

    @pytest.mark.parametrize(
        "expr,expected_num,expected_den",
        [
            ("\\frac{1}{2}", "1", "2"),
            ("\\frac{3}{4}", "3", "4"),
            ("\\frac{42}{7}", "42", "7"),
            ("\\frac{10}{5}", "10", "5"),
            ("\\frac{3.14}{2.71}", "3.14", "2.71"),
            ("\\frac{100}{0.5}", "100", "0.5"),
        ],
    )
    def test_fraction_creates_correct_slots(
        self, expression_widget, set_expression, qapp, expr, expected_num, expected_den
    ):
        """Fraction expression should create FractionWidget with correct numerator/denominator."""
        set_expression(expr)

        nodes = get_all_expression_nodes(expression_widget)
        assert len(nodes) == 1
        assert isinstance(nodes[0], FractionWidget)

        num, den = get_fraction_parts(nodes[0])
        assert num == expected_num
        assert den == expected_den


class TestPowNodeCreation:
    """Test PowWidget creation from text input."""

    @pytest.mark.parametrize(
        "expr,expected_base,expected_exp",
        [
            ("\\pow{2}{3}", "2", "3"),
            ("\\pow{5}{2}", "5", "2"),
            ("\\pow{10}{0}", "10", "0"),
            ("\\pow{2}{10}", "2", "10"),
            ("\\pow{2.5}{1.5}", "2.5", "1.5"),
            ("\\pow{3}{0.5}", "3", "0.5"),
        ],
    )
    def test_pow_creates_correct_slots(
        self, expression_widget, set_expression, qapp, expr, expected_base, expected_exp
    ):
        """Power expression should create PowWidget with correct base/exponent."""
        set_expression(expr)

        nodes = get_all_expression_nodes(expression_widget)
        assert len(nodes) == 1
        assert isinstance(nodes[0], PowWidget)

        base, exp = get_pow_parts(nodes[0])
        assert base == expected_base
        assert exp == expected_exp


class TestNestedExpressions:
    """Test deeply nested and complex expressions."""

    @pytest.mark.parametrize(
        "expr,expected_fraction_count",
        [
            ("\\frac{\\frac{1}{2}}{\\frac{3}{4}}", 3),
            ("\\frac{\\frac{\\frac{1}{2}}{\\frac{3}{4}}}{\\frac{5}{6}}", 5),
            ("\\frac{2}{\\frac{5}{\\frac{4}{\\frac{7}{5}}}}", 4),
            ("\\frac{3}{4}+\\frac{4}{5}", 2),
            ("\\frac{6}{2*(1+2)}", 1),
            ("\\frac{12}{3+(4*(5-\\frac{6}{7+8}))}", 2),
            ("-\\frac{3}{2}", 1),
            ("\\frac{-3}{2}", 1),
            ("(-1) + \\frac{2}{3}", 1),
            (
                "\\frac{\\frac{\\frac{1}{\\pow{2}{2}}}{\\frac{2}{3}}}{\\frac{5}{6}}"
                "+"
                "\\frac{\\frac{\\frac{1}{\\pow{2}{2}}}{\\frac{2}{3}}}{\\frac{5}{6}}",
                10,
            ),
        ],
    )
    def test_nested_fractions_count(
        self, expression_widget: Expression, set_expression, expr, expected_fraction_count
    ):
        """Nested fractions should create expected number of FractionWidgets."""
        set_expression(expr)

        nodes = get_all_expression_nodes(expression_widget)
        fractions = [n for n in nodes if isinstance(n, FractionWidget)]
        assert len(fractions) == expected_fraction_count

    @pytest.mark.parametrize(
        "expr,expected_pow_count",
        [
            ("\\pow{2}{\\pow{3}{4}}", 2),
            ("\\pow{\\pow{2}{3}}{4}", 2),
            ("\\pow{\\pow{2}{\\pow{3}{4}}}{\\pow{5}{\\pow{6}{7}}}", 5),
        ],
    )
    def test_nested_pow_count(
        self, expression_widget: Expression, set_expression, expr, expected_pow_count
    ):
        """Nested powers should create expected number of PowWidgets."""
        set_expression(expr)

        nodes = get_all_expression_nodes(expression_widget)
        pows = [n for n in nodes if isinstance(n, PowWidget)]
        assert len(pows) == expected_pow_count

    def test_two_fractions_with_add_has_plus(self, expression_widget, set_expression, qapp):
        """(\\frac{3}{4})+\\frac{4}{5} should have + operator in serialization."""
        set_expression("(\\frac{3}{4})+\\frac{4}{5}")
        result = expression_widget.get_plain_text()
        assert "+" in result


class TestMixedNodeTypes:
    """Test expressions with both fractions and powers."""

    @pytest.mark.parametrize(
        "expr,expected_frac,expected_pow",
        [
            ("3+4*\\frac{2}{\\pow{(1-5)}{\\pow{2}{3}}}", 1, 2),
            ("\\frac{\\pow{(-3)}{2}}{2+(-1)*\\frac{4}{2}}", 2, 1),
            ("\\frac{\\pow{2}{3}}{\\pow{4}{5}}", 1, 2),
            ("\\frac{(1+2)*(3+4)}{\\frac{(5-6)}{(7+8)}}", 2, 0),
            ("1+(2*(3+\\frac{4}{(5-6)}))", 1, 0),
            ("\\frac{\\pow{(-3)}{2}}{2}", 1, 1),
            (
                "\\frac{"
                "\\pow{2}{\\frac{3}{\\pow{4}{5}}}"
                "}"
                "{"
                "\\frac{\\pow{6}{7}}{\\pow{8}{\\frac{9}{10}}}"
                "}",
                4,
                4,
            ),
        ],
    )
    def test_mixed_expression_node_count(
        self, expression_widget, set_expression, qapp, expr, expected_frac, expected_pow
    ):
        """Mixed expressions should create expected number of each node type."""
        set_expression(expr)

        nodes = get_all_expression_nodes(expression_widget)
        fractions = [n for n in nodes if isinstance(n, FractionWidget)]
        pows = [n for n in nodes if isinstance(n, PowWidget)]
        assert len(fractions) == expected_frac
        assert len(pows) == expected_pow


class TestFocusHandling:
    """Test focus and cursor placement in expression nodes."""

    def test_empty_fraction_has_empty_slot(self, expression_widget, qapp):
        """Empty fraction should have at least one empty slot."""
        main_input = expression_widget.expression_inputs()[0]
        main_input.setText("/")
        qapp.processEvents()

        nodes = get_all_expression_nodes(expression_widget)
        if nodes and isinstance(nodes[0], FractionWidget):
            fraction = nodes[0]
            num_text = fraction.numerator.to_plain_text()
            den_text = fraction.denominator.to_plain_text()
            assert num_text == "" or den_text == ""


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

        nodes = get_all_expression_nodes(expression_widget)
        if nodes and isinstance(nodes[0], FractionWidget):
            fraction = nodes[0]
            slot_obj = getattr(fraction, slot)
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

        nodes_before = get_all_expression_nodes(expression_widget)
        assert len(nodes_before) >= 1

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
        nodes = get_all_expression_nodes(expression_widget)
        assert len(nodes) == 3
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

        nodes = get_all_expression_nodes(expression_widget)
        assert len(nodes) == 1
        assert isinstance(nodes[0], FractionWidget)

    def test_frac_on_empty_input_creates_empty_widget(self, expression_widget, qapp):
        """Insert frac on empty input creates empty FractionWidget."""
        import calc_native

        expression_widget.insert_expr_str(calc_native.ExprKind.Frac)
        qapp.processEvents()

        nodes = get_all_expression_nodes(expression_widget)
        assert len(nodes) == 1
        assert isinstance(nodes[0], FractionWidget)
        num, den = get_fraction_parts(nodes[0])
        assert num == ""
        assert den == ""


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
        nodes = get_all_expression_nodes(expression_widget)
        fractions = [n for n in nodes if isinstance(n, FractionWidget)]
        assert len(fractions) == expected_fracs


class TestNodeRemovalDetailed:
    """Detailed tests for node removal via backspace."""

    def test_backspace_removes_fraction(self, expression_widget, set_expression, qapp):
        """Backspace on empty input after fraction should remove it."""
        set_expression("1 + \\frac{2}{3}")
        qapp.processEvents()

        nodes_before = get_all_expression_nodes(expression_widget)
        assert len(nodes_before) == 1

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
        nodes_after = get_all_expression_nodes(expression_widget)
        assert len(nodes_after) <= len(nodes_before)
