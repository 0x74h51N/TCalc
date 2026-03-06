from __future__ import annotations

from dataclasses import dataclass

import pytest
from calc_native import ParenKind
from PySide6.QtWidgets import QLineEdit

from tcalc.core.ops import Operation
from tcalc.debug import dump_expression_tree, snapshot_tree
from tcalc.ui.widgets.calc.display.expression.expression import Expression
from tcalc.ui.widgets.calc.display.expression.widgets import (
    BraceWidget,
    FractionWidget,
    PowWidget,
    RootWidget,
    RoundParenWidget,
)

DIV_SYM = Operation.DIV.symbol
POW_SYM = Operation.POW.symbol


def _fail_tree(expression_widget: Expression, t, message: str, node=None) -> None:
    dump_expression_tree(expression_widget._root, t.plain_text)
    if node is not None:
        node_dump = "\n".join(["[node_dump]", *node._fmt(0)])
        raise AssertionError(f"{message}\n\n{node_dump}")
    raise AssertionError(f"{message}\n\n{t}")


def _check_indexed(
    expression_widget: Expression,
    t,
    expected: list[tuple[int, object]] | tuple[int, object] | None,
    get_actual,
    label: str,
    get_node=None,
) -> None:
    if expected is None:
        return
    expected_items = expected if isinstance(expected, list) else [expected]
    for idx, value in expected_items:
        actual = get_actual(idx)
        if actual != value:
            node = get_node(idx) if get_node else None
            expected_display = value.__name__ if isinstance(value, type) else value
            actual_display = actual.__name__ if isinstance(actual, type) else actual
            message = f"Expected {label}[{idx}]={expected_display}, got {actual_display}"
            _fail_tree(expression_widget, t, message, node=node)


def _resolve_target_input(expression_widget: Expression, t, path: tuple) -> QLineEdit:
    kind = path[0]
    if kind == "root":
        seg_idx = path[1]
        return expression_widget._root._segments[seg_idx]
    if kind == "node":
        node_idx, slot_name, edit_idx = path[1], path[2], path[3]
        widget = t.all_nodes[node_idx].widget
        slot = getattr(widget, slot_name)
        return slot.line_edits()[edit_idx]
    raise ValueError(f"Unsupported target kind: {kind}")


def _trigger_on_input(
    qapp,
    target: QLineEdit,
    cursor_pos: int,
    action,
    times: int = 1,
) -> None:
    target.setFocus()
    target.setCursorPosition(cursor_pos)
    qapp.processEvents()
    for _ in range(times):
        action()
        qapp.processEvents()


@dataclass(frozen=True)
class ExpressionNodeCase:
    expression: str
    expected_widget_cls_idx: list[tuple[int, type]]
    idx_slot_count: list[tuple[int, int]]
    idx_segment_count: list[tuple[int, int]]
    total_slot_count: int
    total_segment_count: int
    total_edit_count: int


def expression_node_case(**kwargs) -> ExpressionNodeCase:
    return ExpressionNodeCase(**kwargs)


EXPRESSION_NODE_CASES = [
    pytest.param(
        expression_node_case(
            expression="\\frac",
            expected_widget_cls_idx=[(0, FractionWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="fracNode-0",
    ),
    pytest.param(
        expression_node_case(
            expression="\\pow",
            expected_widget_cls_idx=[(0, PowWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="powNode-0",
    ),
    pytest.param(
        expression_node_case(
            expression="\\root",
            expected_widget_cls_idx=[(0, RootWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="rootNode-0",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{1}{2}",
            expected_widget_cls_idx=[(0, FractionWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="fracNode-1",
    ),
    pytest.param(
        expression_node_case(
            expression="\\pow{2}{3}",
            expected_widget_cls_idx=[(0, PowWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="powNode-1",
    ),
    pytest.param(
        expression_node_case(
            expression="\\root{2}{3}",
            expected_widget_cls_idx=[(0, RootWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="rootNode-1",
    ),
    pytest.param(
        expression_node_case(
            expression="1+\\frac{1}{2}",
            expected_widget_cls_idx=[(0, FractionWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="frac-plus",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{1}{2}+\\frac{3}{4}",
            expected_widget_cls_idx=[(0, FractionWidget), (1, FractionWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 2), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="frac-plus-frac",
    ),
    pytest.param(
        expression_node_case(
            expression="1+\\pow{2}{3}",
            expected_widget_cls_idx=[(0, PowWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="pow-plus",
    ),
    pytest.param(
        expression_node_case(
            expression="1+\\root{2}{3}",
            expected_widget_cls_idx=[(0, RootWidget)],
            idx_slot_count=[(0, 2)],
            idx_segment_count=[(0, 2)],
            total_slot_count=2,
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="root-plus",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{1}{2}\\root{2}{3}",
            expected_widget_cls_idx=[(0, FractionWidget), (1, RootWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 2), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="implicit-multiplation-nodes",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{\\frac{1}{2}}{3}",
            expected_widget_cls_idx=[(0, FractionWidget), (1, FractionWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="frac-nested-left",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{\\frac{1}{2}}{\\frac{3}{4}}",
            expected_widget_cls_idx=[
                (0, FractionWidget),
                (1, FractionWidget),
                (2, FractionWidget),
            ],
            idx_slot_count=[(0, 2), (1, 2), (2, 2)],
            idx_segment_count=[(0, 6), (1, 2), (2, 2)],
            total_slot_count=6,
            total_segment_count=13,
            total_edit_count=10,
        ),
        id="frac-nested-both",
    ),
    pytest.param(
        expression_node_case(
            expression="\\pow{2}{\\pow{3}{4}}",
            expected_widget_cls_idx=[(0, PowWidget), (1, PowWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="pow-nested-exp",
    ),
    pytest.param(
        expression_node_case(
            expression="\\pow{\\pow{2}{3}}{4}",
            expected_widget_cls_idx=[(0, PowWidget), (1, PowWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="pow-nested-base",
    ),
    pytest.param(
        expression_node_case(
            expression="\\root{2}{\\root{3}{4}}",
            expected_widget_cls_idx=[(0, RootWidget), (1, RootWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="root-nested-radicand",
    ),
    pytest.param(
        expression_node_case(
            expression="\\root{\\root{2}{3}}{4}",
            expected_widget_cls_idx=[(0, RootWidget), (1, RootWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="root-nested-degree",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{\\pow{2}{3}}{\\pow{4}{5}}",
            expected_widget_cls_idx=[
                (0, FractionWidget),
                (1, PowWidget),
                (2, PowWidget),
            ],
            idx_slot_count=[(0, 2), (1, 2), (2, 2)],
            idx_segment_count=[(0, 6), (1, 2), (2, 2)],
            total_slot_count=6,
            total_segment_count=13,
            total_edit_count=10,
        ),
        id="frac-with-two-pows",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{\\pow{2}{3}}{\\root{4}{5}}",
            expected_widget_cls_idx=[
                (0, FractionWidget),
                (1, PowWidget),
                (2, RootWidget),
            ],
            idx_slot_count=[(0, 2), (1, 2), (2, 2)],
            idx_segment_count=[(0, 6), (1, 2), (2, 2)],
            total_slot_count=6,
            total_segment_count=13,
            total_edit_count=10,
        ),
        id="frac-with-pow-root",
    ),
    pytest.param(
        expression_node_case(
            expression="\\pow{\\frac{1}{2}}{\\root{2}{3}}",
            expected_widget_cls_idx=[
                (0, PowWidget),
                (1, FractionWidget),
                (2, RootWidget),
            ],
            idx_slot_count=[(0, 2), (1, 2), (2, 2)],
            idx_segment_count=[(0, 6), (1, 2), (2, 2)],
            total_slot_count=6,
            total_segment_count=13,
            total_edit_count=10,
        ),
        id="pow-with-frac-root",
    ),
    pytest.param(
        expression_node_case(
            expression="\\root{2}{\\frac{\\pow{3}{4}}{5}}",
            expected_widget_cls_idx=[
                (0, RootWidget),
                (1, FractionWidget),
                (2, PowWidget),
            ],
            idx_slot_count=[(0, 2), (1, 2), (2, 2)],
            idx_segment_count=[(0, 4), (1, 4), (2, 2)],
            total_slot_count=6,
            total_segment_count=13,
            total_edit_count=10,
        ),
        id="root-with-frac-pow",
    ),
    pytest.param(
        expression_node_case(
            expression="\\frac{1+\\pow{2}{3}}{4}",
            expected_widget_cls_idx=[(0, FractionWidget), (1, PowWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="frac-nested-with-text",
    ),
    pytest.param(
        expression_node_case(
            expression="\\pow{1+\\frac{2}{3}}{4}",
            expected_widget_cls_idx=[(0, PowWidget), (1, FractionWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="pow-nested-with-text",
    ),
    pytest.param(
        expression_node_case(
            expression="\\root{1+\\pow{2}{3}}{4}",
            expected_widget_cls_idx=[(0, RootWidget), (1, PowWidget)],
            idx_slot_count=[(0, 2), (1, 2)],
            idx_segment_count=[(0, 4), (1, 2)],
            total_slot_count=4,
            total_segment_count=9,
            total_edit_count=7,
        ),
        id="root-nested-with-text",
    ),
]


@pytest.mark.parametrize("case", EXPRESSION_NODE_CASES)
class TestExpressionNode:
    """Test expressions with fractions, powers, and roots."""

    def _snapshot(self, expression_widget, set_expression, expression):
        set_expression(expression)
        return snapshot_tree(expression_widget)

    def test_node_classes(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            case.expected_widget_cls_idx,
            get_actual=lambda idx: type(t.all_nodes[idx].widget),
            label="node class",
            get_node=lambda idx: t.all_nodes[idx],
        )

    def test_node_slot_counts(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            case.idx_slot_count,
            get_actual=lambda idx: len(t.all_nodes[idx].slots),
            label="node slot count",
            get_node=lambda idx: t.all_nodes[idx],
        )

    def test_node_segment_counts(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            case.idx_segment_count,
            get_actual=lambda idx: sum(len(slot.segments) for slot in t.all_nodes[idx].slots),
            label="node segment count",
            get_node=lambda idx: t.all_nodes[idx],
        )

    def test_total_slot_count(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        total_slots = sum(len(node.slots) for node in t.all_nodes)
        _check_indexed(
            expression_widget,
            t,
            [(0, case.total_slot_count)],
            get_actual=lambda _: total_slots,
            label="total slot count",
        )

    def test_total_segment_count(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        total_segments = sum(len(slot.segments) for slot in t.all_slots)
        _check_indexed(
            expression_widget,
            t,
            [(0, case.total_segment_count)],
            get_actual=lambda _: total_segments,
            label="total segment count",
        )

    def test_total_edit_count(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            [(0, case.total_edit_count)],
            get_actual=lambda _: len(t.all_edits),
            label="total edit count",
        )


@dataclass(frozen=True)
class ParenWidgetCase:
    expression: str
    expected_count: int
    expected_parenKind_idx: list[tuple[int, ParenKind]]
    idx_segments_count: list[tuple[int, int]]
    total_segment_count: int
    total_edit_count: int


def paren_widget_case(**kwargs) -> ParenWidgetCase:
    return ParenWidgetCase(**kwargs)


PAREN_WIDGET_CASES = [
    pytest.param(
        paren_widget_case(
            expression="(1)+\\frac{2}{3}",
            expected_count=0,
            expected_parenKind_idx=[],
            idx_segments_count=[],
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="non-parenNode",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+\\frac{2}{3})",
            expected_count=0,
            expected_parenKind_idx=[],
            idx_segments_count=[],
            total_segment_count=5,
            total_edit_count=4,
        ),
        id="non-parenNode-w-close",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+(\\frac{2}{3})",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Paren)],
            idx_segments_count=[(0, 5)],
            total_segment_count=10,
            total_edit_count=6,
        ),
        id="render-parenNode",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+(2+\\frac{2}{3})",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Paren)],
            idx_segments_count=[(0, 5)],
            total_segment_count=10,
            total_edit_count=6,
        ),
        id="paren-with-prefix-text",
    ),
    pytest.param(
        paren_widget_case(
            expression="{\\frac{2}{3}}",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Brace)],
            idx_segments_count=[(0, 5)],
            total_segment_count=10,
            total_edit_count=6,
        ),
        id="brace-widget",
    ),
    pytest.param(
        paren_widget_case(
            expression="{\\frac{2}{3})",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Brace)],
            idx_segments_count=[(0, 4)],
            total_segment_count=8,
            total_edit_count=5,
        ),
        id="non-closed-brace-widget",
    ),
    pytest.param(
        paren_widget_case(
            expression="{+\\frac{2}{3}",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Brace)],
            idx_segments_count=[(0, 4)],
            total_segment_count=8,
            total_edit_count=5,
        ),
        id="open-brace-leading-op",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+{2+\\root{2}{3}}",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Brace)],
            idx_segments_count=[(0, 5)],
            total_segment_count=10,
            total_edit_count=6,
        ),
        id="brace-in-sum",
    ),
    pytest.param(
        paren_widget_case(
            expression="[\\frac{2}{3}]",
            expected_count=1,
            expected_parenKind_idx=[(0, ParenKind.Bracket)],
            idx_segments_count=[(0, 5)],
            total_segment_count=10,
            total_edit_count=6,
        ),
        id="bracket-widget",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+{2+[\\pow{2}{3}]+4}",
            expected_count=2,
            expected_parenKind_idx=[(0, ParenKind.Brace), (1, ParenKind.Bracket)],
            idx_segments_count=[(0, 5), (1, 5)],
            total_segment_count=15,
            total_edit_count=8,
        ),
        id="outer-first-nested-parens",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+{2+[\\frac{2}{3}+4+(\\pow{2}{3})]}",
            expected_count=3,
            expected_parenKind_idx=[
                (0, ParenKind.Brace),
                (1, ParenKind.Bracket),
                (2, ParenKind.Paren),
            ],
            idx_segments_count=[(0, 5), (1, 7), (2, 5)],
            total_segment_count=24,
            total_edit_count=13,
        ),
        id="nested-brace-bracket-paren",
    ),
    pytest.param(
        paren_widget_case(
            expression="(1)+{2+[\\frac{2}{3}+4+(\\pow{2}{3}",
            expected_count=3,
            expected_parenKind_idx=[
                (0, ParenKind.Brace),
                (1, ParenKind.Bracket),
                (2, ParenKind.Paren),
            ],
            idx_segments_count=[(0, 3), (1, 5), (2, 4)],
            total_segment_count=18,
            total_edit_count=10,
        ),
        id="nested-brace-bracket-paren-open-only",
    ),
]


@pytest.mark.parametrize("case", PAREN_WIDGET_CASES)
class TestParenWidget:
    """Test readyExpression ParenWidget render pipeline."""

    def _snapshot(self, expression_widget, set_expression, expression):
        set_expression(expression)
        return snapshot_tree(expression_widget)

    def test_paren_count(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        if len(t.parens) != case.expected_count:
            _fail_tree(
                expression_widget,
                t,
                f"Expected {case.expected_count} ParenWidget(s), got {len(t.parens)}",
            )

    def test_paren_kinds(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            case.expected_parenKind_idx,
            get_actual=lambda idx: t.parens[idx].paren_kind,
            label="ParenWidget kind",
        )

    def test_paren_segments(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            case.idx_segments_count,
            get_actual=lambda idx: len(t.parens[idx].slots[0].segments),
            label="ParenWidget segments",
            get_node=lambda idx: t.parens[idx],
        )

    def test_total_segment_count(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        total_segments = sum(len(slot.segments) for slot in t.all_slots)
        _check_indexed(
            expression_widget,
            t,
            [(0, case.total_segment_count)],
            get_actual=lambda _: total_segments,
            label="total segment count",
        )

    def test_total_edit_count(self, expression_widget, set_expression, case):
        t = self._snapshot(expression_widget, set_expression, case.expression)
        _check_indexed(
            expression_widget,
            t,
            [(0, case.total_edit_count)],
            get_actual=lambda _: len(t.all_edits),
            label="total edit count",
        )


#
#
#
# UI Integration Tests


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


@dataclass(frozen=True)
class NodeInsertCase:
    init_expr: str
    target_path: tuple
    cursor_pos: int
    insert_str: str
    expected_widget_cls_idx: list[tuple[int, type]]
    expected_inner_segments_idx: list[tuple[int, int]]
    total_node_count: int
    total_segment_count: int
    total_edit_count: int
    expected_plain_text: str


def node_insert_case(**kwargs) -> NodeInsertCase:
    return NodeInsertCase(**kwargs)


NODE_INSERT_CASES = [
    pytest.param(
        node_insert_case(
            init_expr="\\frac{1}{2}",
            target_path=("root", 2),
            cursor_pos=0,
            insert_str="\\pow",
            expected_widget_cls_idx=[(1, PowWidget)],
            expected_inner_segments_idx=[(1, 2)],
            total_node_count=2,
            total_segment_count=9,
            total_edit_count=7,
            expected_plain_text="\\frac{1}{2}\\pow{}{}",
        ),
        id="insert-pow-after-frac",
    ),
    pytest.param(
        node_insert_case(
            init_expr="\\pow{2}{3}",
            target_path=("node", 0, "exponent", 0),
            cursor_pos=1,
            insert_str="\\frac",
            expected_widget_cls_idx=[(1, FractionWidget)],
            expected_inner_segments_idx=[(1, 2)],
            total_node_count=2,
            total_segment_count=9,
            total_edit_count=7,
            expected_plain_text="\\pow{2}{\\frac{3}{}}",
        ),
        id="insert-frac-into-exponent",
    ),
    pytest.param(
        node_insert_case(
            init_expr="\\frac{1}{2}",
            target_path=("node", 0, "denominator", 0),
            cursor_pos=1,
            insert_str="\\root",
            expected_widget_cls_idx=[(0, FractionWidget), (1, RootWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=9,
            total_edit_count=7,
            expected_plain_text="\\frac{1}{\\root{2}{}}",
        ),
        id="insert-root-into-denom",
    ),
    pytest.param(
        node_insert_case(
            init_expr="12+\\frac{3}{4}",
            target_path=("root", 0),
            cursor_pos=1,
            insert_str="\\pow",
            expected_widget_cls_idx=[(0, PowWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 2), (1, 2)],
            total_node_count=2,
            total_segment_count=9,
            total_edit_count=7,
            expected_plain_text="\\pow{1}{2} + \\frac{3}{4}",
        ),
        id="add-node-between-numbers",
    ),
    pytest.param(
        node_insert_case(
            init_expr="\\frac{1}{2}\\frac{3}{4}",
            target_path=("root", 2),
            cursor_pos=0,
            insert_str="(",
            expected_widget_cls_idx=[
                (0, FractionWidget),
                (1, RoundParenWidget),
                (2, FractionWidget),
            ],
            expected_inner_segments_idx=[(0, 2), (1, 4), (2, 2)],
            total_node_count=3,
            total_segment_count=12,
            total_edit_count=8,
            expected_plain_text="\\frac{1}{2}(\\frac{3}{4}",
        ),
        id="open-paren-wrap-right-frac",
    ),
    pytest.param(
        node_insert_case(
            init_expr="\\frac{3}{4}",
            target_path=("root", 0),
            cursor_pos=0,
            insert_str="(",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="(\\frac{3}{4}",
        ),
        id="try-open-paren-0",
    ),
    pytest.param(
        node_insert_case(
            init_expr="1+2+\\frac{3}{4}",
            target_path=("root", 0),
            cursor_pos=0,
            insert_str="(",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="(1 + 2 + \\frac{3}{4}",
        ),
        id="try-open-paren-1",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{3}{4}",
            target_path=("root", 0),
            cursor_pos=0,
            insert_str="{",
            expected_widget_cls_idx=[(0, BraceWidget), (1, RoundParenWidget), (2, FractionWidget)],
            expected_inner_segments_idx=[(0, 3), (1, 4), (2, 2)],
            total_node_count=3,
            total_segment_count=11,
            total_edit_count=6,
            expected_plain_text="{(1 + 2 + \\frac{3}{4}",
        ),
        id="try-open-paren-nested-paren-outer",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{3}{4}",
            target_path=("node", 0, "_left_slot", 0),
            cursor_pos=4,
            insert_str="{",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, BraceWidget), (2, FractionWidget)],
            expected_inner_segments_idx=[(0, 3), (1, 4), (2, 2)],
            total_node_count=3,
            total_segment_count=11,
            total_edit_count=6,
            expected_plain_text="(1 + {2 + \\frac{3}{4}",
        ),
        id="try-open-paren-nested-paren-inner",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{\\root{3}{5}}{4}",
            target_path=("node", 1, "numerator", 0),
            cursor_pos=0,
            insert_str="{",
            expected_widget_cls_idx=[
                (0, RoundParenWidget),
                (1, FractionWidget),
                (2, BraceWidget),
                (3, RootWidget),
            ],
            expected_inner_segments_idx=[(0, 4), (1, 3), (2, 4), (3, 2)],
            total_node_count=4,
            total_segment_count=15,
            total_edit_count=9,
            expected_plain_text="(1 + 2 + \\frac{{\\root{3}{5}}{4}",
        ),
        id="try-open-paren-nested-node",
    ),
    pytest.param(
        node_insert_case(
            init_expr="1+2)+\\frac{3}{4}",
            target_path=("root", 0),
            cursor_pos=0,
            insert_str="(",
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="(1 + 2) + \\frac{3}{4}",
        ),
        id="try-open-paren-non-paren-before-non-node-close",
    ),
    pytest.param(
        node_insert_case(
            init_expr="1+2+\\frac{3}{4}+5",
            target_path=("root", 2),
            cursor_pos=0,
            insert_str="(",
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="1 + 2 + \\frac{3}{4}(+5",
        ),
        id="try-open-paren-non-paren-after-node",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{3}{4}",
            target_path=("node", 0, "_left_slot", -1),
            cursor_pos=0,
            insert_str=")",
            expected_widget_cls_idx=[(0, RoundParenWidget)],
            expected_inner_segments_idx=[(0, 5)],
            total_node_count=2,
            total_segment_count=10,
            total_edit_count=6,
            expected_plain_text="(1 + 2 + \\frac{3}{4})",
        ),
        id="try-close-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{3}{4}",
            target_path=("node", 0, "_left_slot", -1),
            cursor_pos=0,
            insert_str="}",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="(1 + 2 + \\frac{3}{4}}",
        ),
        id="try-close-paren-non-paren-diff-kind",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{3}{4}",
            target_path=("node", 0, "_left_slot", 0),
            cursor_pos=5,
            insert_str=")",
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="(1 + 2) + \\frac{3}{4}",
        ),
        id="try-close-paren-non-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(1+2+\\frac{3}{4}",
            target_path=("node", 1, "numerator", 0),
            cursor_pos=1,
            insert_str=")",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="(1 + 2 + \\frac{3)}{4}",
        ),
        id="try-close-paren-non-paren-at-child-seg",
    ),
    pytest.param(
        node_insert_case(
            init_expr="{1+(2+3+\\frac{3}{4}+5",
            target_path=("node", 1, "_left_slot", -1),
            cursor_pos=0,
            insert_str="}",
            expected_widget_cls_idx=[(0, BraceWidget), (1, RoundParenWidget), (2, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 4), (2, 2)],
            total_node_count=3,
            total_segment_count=13,
            total_edit_count=7,
            expected_plain_text="{1 + (2 + 3 + \\frac{3}{4}} + 5",
        ),
        marks=pytest.mark.xfail(reason="_try_close_paren runs inner first, outer not closed"),
        id="try-close-paren-nested-paren-outer",
    ),
    pytest.param(
        node_insert_case(
            init_expr="{1+(2+3+\\frac{3}{4}+5",
            target_path=("node", 1, "_left_slot", -1),
            cursor_pos=0,
            insert_str=")",
            expected_widget_cls_idx=[(0, BraceWidget), (1, RoundParenWidget), (2, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 5), (2, 2)],
            total_node_count=3,
            total_segment_count=13,
            total_edit_count=7,
            expected_plain_text="{1 + (2 + 3 + \\frac{3}{4}) + 5",
        ),
        id="try-close-paren-nested-paren-inner",
    ),
    pytest.param(
        node_insert_case(
            init_expr="{1+(2+3+\\frac{3}{4}+5",
            target_path=("node", 1, "_left_slot", 0),
            cursor_pos=5,
            insert_str=")",
            expected_widget_cls_idx=[(0, BraceWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="{1 + (2 + 3) + \\frac{3}{4} + 5",
        ),
        id="try-close-paren-nested-paren-inner-non-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="{1+(2+3+\\frac{3}{4}+5",
            target_path=("node", 1, "_left_slot", 0),
            cursor_pos=5,
            insert_str="}",
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="{1 + (2 + 3} + \\frac{3}{4} + 5",
        ),
        marks=pytest.mark.xfail(reason="_try_close_paren runs inner first, outer not closed"),
        id="try-close-paren-nested-paren-outer-none-paren-all",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(\\frac{1}{2}",
            target_path=("node", 0, "_left_slot", 0),
            cursor_pos=0,
            insert_str="3+\\pow+",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, PowWidget), (2, FractionWidget)],
            expected_inner_segments_idx=[(0, 6), (1, 2), (2, 2)],
            total_node_count=3,
            total_segment_count=12,
            total_edit_count=8,
            expected_plain_text="(3 + \\pow{}{} + \\frac{1}{2}",
        ),
        id="insert-node-inside-open-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(2 + ",
            target_path=("root", 0),
            cursor_pos=5,
            insert_str="3+\\pow",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, PowWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="(2 + 3 + \\pow{}{}",
        ),
        id="insert-node-into-flat-open-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(2 + ",
            target_path=("root", 0),
            cursor_pos=5,
            insert_str="3+\\pow{4}{5}+6)",
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, PowWidget)],
            expected_inner_segments_idx=[(0, 5), (1, 2)],
            total_node_count=2,
            total_segment_count=10,
            total_edit_count=6,
            expected_plain_text="(2 + 3 + \\pow{4}{5} + 6)",
        ),
        id="insert-node-and-close-paren-into-flat-open-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(\\frac{1}{2}+3)",
            target_path=("node", 0, "_left_slot", -1),
            cursor_pos=1,
            insert_str="\\pow",
            expected_widget_cls_idx=[
                (0, RoundParenWidget),
                (1, FractionWidget),
                (2, PowWidget),
            ],
            expected_inner_segments_idx=[(0, 7), (1, 2), (2, 2)],
            total_node_count=3,
            total_segment_count=14,
            total_edit_count=9,
            expected_plain_text="(\\frac{1}{2}\\pow{}{} + 3)",
        ),
        id="insert-node-after-node-in-closed-paren",
    ),
    pytest.param(
        node_insert_case(
            init_expr="\\frac{1}{2}",
            target_path=("root", 2),
            cursor_pos=0,
            insert_str="+\\frac",
            expected_widget_cls_idx=[(0, FractionWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 2), (1, 2)],
            total_node_count=2,
            total_segment_count=9,
            total_edit_count=7,
            expected_plain_text="\\frac{1}{2} + \\frac{}{}",
        ),
        id="insert-frac-in-suffix-of-frac",
    ),
    pytest.param(
        node_insert_case(
            init_expr="(\\frac{1}{2}",
            target_path=("node", 0, "_left_slot", -1),
            cursor_pos=0,
            insert_str=")",
            expected_widget_cls_idx=[(0, RoundParenWidget)],
            expected_inner_segments_idx=[(0, 5)],
            total_node_count=2,
            total_segment_count=10,
            total_edit_count=6,
            expected_plain_text="(\\frac{1}{2})",
        ),
        id="close-paren-right-after-node",
    ),
]


@pytest.mark.parametrize("rendered_case", NODE_INSERT_CASES, indirect=True)
class TestNodeInsertAfterRender:
    @pytest.fixture(scope="class")
    def rendered_case(self, request, qapp):
        case = request.param
        widget = Expression()
        widget.show()
        widget.set_plain_text(case.init_expr)
        qapp.processEvents()

        t_before = snapshot_tree(widget)
        target = _resolve_target_input(widget, t_before, case.target_path)
        if not isinstance(target, QLineEdit):
            _fail_tree(
                widget,
                t_before,
                f"Expected QLineEdit target, got {type(target).__name__}",
            )

        target.setFocus()
        target.setCursorPosition(case.cursor_pos)
        target.insert(case.insert_str)
        qapp.processEvents()
        t_after = snapshot_tree(widget)

        yield case, widget, t_after

        widget.close()
        widget.deleteLater()
        qapp.processEvents()

    def test_node_classes(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            case.expected_widget_cls_idx,
            get_actual=lambda idx: type(t_after.all_nodes[idx].widget),
            label="node class",
            get_node=lambda idx: t_after.all_nodes[idx],
        )

    def test_node_segments(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            case.expected_inner_segments_idx,
            get_actual=lambda idx: sum(len(slot.segments) for slot in t_after.all_nodes[idx].slots),
            label="node segment count",
            get_node=lambda idx: t_after.all_nodes[idx],
        )

    def test_total_nodes(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            [(0, case.total_node_count)],
            get_actual=lambda _: len(t_after.all_nodes),
            label="total node count",
        )

    def test_total_segments(self, rendered_case):
        case, widget, t_after = rendered_case
        total_segments = sum(len(slot.segments) for slot in t_after.all_slots)
        _check_indexed(
            widget,
            t_after,
            [(0, case.total_segment_count)],
            get_actual=lambda _: total_segments,
            label="total segment count",
        )

    def test_total_edits(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            [(0, case.total_edit_count)],
            get_actual=lambda _: len(t_after.all_edits),
            label="total edit count",
        )

    def test_plain_text(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            [(0, case.expected_plain_text)],
            get_actual=lambda _: widget.get_plain_text(),
            label="plain text",
        )


@dataclass(frozen=True)
class FlatNegateCase:
    text: str
    cursor: int
    expected: str


@dataclass(frozen=True)
class ExprNegateCase:
    expression: str
    target_path: tuple
    cursor_pos: int
    negate_times: int
    expected_plain_text: str
    expected_plain_text_first: str | None


def flat_negate_case(**kwargs) -> FlatNegateCase:
    return FlatNegateCase(**kwargs)


def expr_negate_case(**kwargs) -> ExprNegateCase:
    return ExprNegateCase(**kwargs)


class TestHandleNegate:
    """Test handle_negate toggling unary minus based on cursor position."""

    @pytest.mark.parametrize(
        "flat_case",
        [
            pytest.param(
                flat_negate_case(text="4", cursor=1, expected="-4"),
                id="simple-number",
            ),
            pytest.param(
                flat_negate_case(text="-4", cursor=2, expected="4"),
                id="toggle-back",
            ),
            pytest.param(
                flat_negate_case(text="4 + 6", cursor=5, expected="4 + -6"),
                id="after-binary-op",
            ),
            pytest.param(
                flat_negate_case(text="(4 + 6", cursor=6, expected="(4 + -6"),
                id="unclosed-paren",
            ),
            pytest.param(
                flat_negate_case(text="(4 + 6)", cursor=7, expected="-(4 + 6)"),
                id="closed-paren",
            ),
            pytest.param(
                flat_negate_case(text="-(4 + 6)", cursor=8, expected="(4 + 6)"),
                id="toggle-back-closed",
            ),
            pytest.param(
                flat_negate_case(text="", cursor=0, expected="-"),
                id="empty-input",
            ),
            pytest.param(
                flat_negate_case(text="-", cursor=1, expected=""),
                id="just-minus",
            ),
            pytest.param(
                flat_negate_case(text="3(4 + 3)", cursor=4, expected="3(-4 + 3)"),
                id="cursor-mid",
            ),
            pytest.param(
                flat_negate_case(text="3(4 + 3)", cursor=2, expected="3(-4 + 3)"),
                id="cursor-inner-start",
            ),
            pytest.param(
                flat_negate_case(text="2 + 3", cursor=5, expected="2 + -3"),
                id="after-operator",
            ),
            pytest.param(
                flat_negate_case(text="2 + (3 + 4)", cursor=11, expected="2 + -(3 + 4)"),
                id="closed-paren-after-operator",
            ),
        ],
    )
    def test_negate_flat_text(self, expression_widget, qapp, flat_case):
        """handle_negate on flat text (no ExpressionNodes) with cursor positioning."""
        target = expression_widget._resolve_target()
        target.setText(flat_case.text)
        _trigger_on_input(
            qapp,
            target,
            flat_case.cursor,
            expression_widget.handle_negate,
            1,
        )
        assert target.text() == flat_case.expected, (
            f"negate({flat_case.text!r}, cursor={flat_case.cursor})"
            f" -> {target.text()!r}, expected {flat_case.expected!r}"
        )

    def _run_expr_negate(self, expression_widget, set_expression, qapp, expr_case):
        set_expression(expr_case.expression)

        t = snapshot_tree(expression_widget)
        target = _resolve_target_input(expression_widget, t, expr_case.target_path)

        _trigger_on_input(
            qapp,
            target,
            expr_case.cursor_pos,
            expression_widget.handle_negate,
            1,
        )
        first_text = expression_widget.get_plain_text()
        remaining = max(0, expr_case.negate_times - 1)
        _trigger_on_input(
            qapp,
            target,
            expr_case.cursor_pos,
            expression_widget.handle_negate,
            remaining,
        )
        final_text = expression_widget.get_plain_text()
        return first_text, final_text

    @pytest.mark.parametrize(
        "expr_case",
        [
            pytest.param(
                expr_negate_case(
                    expression="\\frac{3}{4}",
                    target_path=("node", 0, "numerator", 0),
                    cursor_pos=1,
                    negate_times=1,
                    expected_plain_text="\\frac{-3}{4}",
                    expected_plain_text_first=None,
                ),
                id="negate-frac-num",
            ),
            pytest.param(
                expr_negate_case(
                    expression="\\frac{3}{4}",
                    target_path=("node", 0, "denominator", 0),
                    cursor_pos=1,
                    negate_times=1,
                    expected_plain_text="\\frac{3}{-4}",
                    expected_plain_text_first=None,
                ),
                id="negate-frac-den",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\frac{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=1,
                    expected_plain_text="1 + -\\frac{2}{3}",
                    expected_plain_text_first=None,
                ),
                id="negate-after-frac",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\frac{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="1 + \\frac{2}{3}",
                    expected_plain_text_first="1 + -\\frac{2}{3}",
                ),
                id="negate-after-frac-toggle",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\pow{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=1,
                    expected_plain_text="1 + -\\pow{2}{3}",
                    expected_plain_text_first=None,
                ),
                id="negate-after-pow",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\pow{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="1 + \\pow{2}{3}",
                    expected_plain_text_first="1 + -\\pow{2}{3}",
                ),
                id="negate-after-pow-toggle",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\root{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=1,
                    expected_plain_text="1 + -\\root{2}{3}",
                    expected_plain_text_first=None,
                ),
                id="negate-after-root",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\root{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="1 + \\root{2}{3}",
                    expected_plain_text_first="1 + -\\root{2}{3}",
                ),
                id="negate-after-root-toggle",
            ),
            pytest.param(
                expr_negate_case(
                    expression="\\frac{1}{2}\\frac{3}{4}",
                    target_path=("root", 4),
                    cursor_pos=0,
                    negate_times=1,
                    expected_plain_text="\\frac{1}{2} - \\frac{3}{4}",
                    expected_plain_text_first=None,
                ),
                id="negate-before-fracs",
            ),
            pytest.param(
                expr_negate_case(
                    expression="\\frac{2}{3}\\frac{4}{5}",
                    target_path=("root", 2),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="\\frac{2}{3}\\frac{4}{5}",
                    expected_plain_text_first="-\\frac{2}{3}\\frac{4}{5}",
                ),
                id="negate-between-fracs-toggle",
            ),
        ],
    )
    def test_negate_expression_nodes_final(
        self, expression_widget, set_expression, qapp, expr_case
    ):
        """Negate behavior around expression nodes."""
        _, final_text = self._run_expr_negate(expression_widget, set_expression, qapp, expr_case)
        _check_indexed(
            expression_widget,
            snapshot_tree(expression_widget),
            [(0, expr_case.expected_plain_text)],
            get_actual=lambda _: final_text,
            label="plain text",
        )

    @pytest.mark.parametrize(
        "expr_case",
        [
            pytest.param(
                expr_negate_case(
                    expression="1 + \\frac{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="1 + \\frac{2}{3}",
                    expected_plain_text_first="1 + -\\frac{2}{3}",
                ),
                id="negate-after-frac-toggle",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\pow{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="1 + \\pow{2}{3}",
                    expected_plain_text_first="1 + -\\pow{2}{3}",
                ),
                id="negate-after-pow-toggle",
            ),
            pytest.param(
                expr_negate_case(
                    expression="1 + \\root{2}{3}",
                    target_path=("root", -1),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="1 + \\root{2}{3}",
                    expected_plain_text_first="1 + -\\root{2}{3}",
                ),
                id="negate-after-root-toggle",
            ),
            pytest.param(
                expr_negate_case(
                    expression="\\frac{2}{3}\\frac{4}{5}",
                    target_path=("root", 2),
                    cursor_pos=0,
                    negate_times=2,
                    expected_plain_text="\\frac{2}{3}\\frac{4}{5}",
                    expected_plain_text_first="-\\frac{2}{3}\\frac{4}{5}",
                ),
                id="negate-between-fracs-toggle",
            ),
        ],
    )
    def test_negate_expression_nodes_first(
        self, expression_widget, set_expression, qapp, expr_case
    ):
        first_text, _ = self._run_expr_negate(expression_widget, set_expression, qapp, expr_case)
        _check_indexed(
            expression_widget,
            snapshot_tree(expression_widget),
            [(0, expr_case.expected_plain_text_first)],
            get_actual=lambda _: first_text,
            label="plain text",
        )


@dataclass(frozen=True)
class NodeBackspaceCase:
    init_expr: str
    target_path: tuple
    cursor_pos: int
    expected_widget_cls_idx: list[tuple[int, type]] | None
    expected_inner_segments_idx: list[tuple[int, int]] | None
    total_node_count: int
    total_segment_count: int
    total_edit_count: int
    expected_plain_text: str
    expected_focus_cursor: tuple[tuple, int] | None = None


def node_backspace_case(**kwargs) -> NodeBackspaceCase:
    return NodeBackspaceCase(**kwargs)


NODE_BACKSPACE_CASES = [
    pytest.param(
        node_backspace_case(
            init_expr="\\frac{2}{}",
            target_path=("node", 0, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="2",
            expected_focus_cursor=(("root", 0), 1),
        ),
        id="dissolve-frac-empty-denom",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="\\pow{2}{}",
            target_path=("node", 0, "exponent", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="2",
            expected_focus_cursor=(("root", 0), 1),
        ),
        id="dissolve-pow-empty-exp",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="\\root{2}{}",
            target_path=("node", 0, "radicand", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="2",
            expected_focus_cursor=(("root", 0), 1),
        ),
        id="dissolve-root-empty-radicand",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="1 + \\frac{2}{} + 3",
            target_path=("node", 0, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="1 + 2 + 3",
            expected_focus_cursor=(("root", 0), 5),
        ),
        id="dissolve-frac-with-surrounding",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="1 + \\pow{2}{} + 3",
            target_path=("node", 0, "exponent", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="1 + 2 + 3",
            expected_focus_cursor=(("root", 0), 5),
        ),
        id="dissolve-pow-with-surrounding",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="\\frac{\\frac{2}{}}{3}",
            target_path=("node", 1, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="\\frac{2}{3}",
            expected_focus_cursor=(
                ("node", 0, "numerator", 0),
                1,
            ),  # (("node", 0, "numerator", 0), 1),
        ),
        id="dissolve-nested-frac-inner-denom",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="\\frac{\\frac{2}{4}}{} + 5",
            target_path=("node", 0, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="\\frac{2}{4} + 5",
        ),
        id="dissolve-outer-frac-keeps-inner",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="(\\frac{2}{4})",
            target_path=("root", -1),
            cursor_pos=0,
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 4), (1, 2)],
            total_node_count=2,
            total_segment_count=8,
            total_edit_count=5,
            expected_plain_text="(\\frac{2}{4}",
            expected_focus_cursor=None,  # xFail it should be (("node", 0, "_left_slot", -1), 0)
        ),
        id="non-dissolve-paren-w-remove-close",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="(\\frac{2}{4}",
            target_path=("node", 0, "_left_slot", 0),
            cursor_pos=0,
            expected_widget_cls_idx=[(0, FractionWidget)],
            expected_inner_segments_idx=[(0, 2)],
            total_node_count=1,
            total_segment_count=5,
            total_edit_count=4,
            expected_plain_text="\\frac{2}{4}",
            expected_focus_cursor=(("node", 0, "denominator", 0), 1),
        ),
        id="dissolve-paren-w-remove-open",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="(\\frac{2}{}+4)",
            target_path=("node", 1, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="(2 + 4)",
            expected_focus_cursor=(("root", 0), 2),
        ),
        id="dissolve-frac-and-paren-closed",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="(\\frac{2}{} + 4",
            target_path=("node", 1, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="(2 + 4",
            expected_focus_cursor=(("root", 0), 2),
        ),
        id="dissolve-frac-and-paren-unclosed",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="(2 + \\frac{3}{} + 4",
            target_path=("node", 1, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="(2 + 3 + 4",
            expected_focus_cursor=(("root", 0), 6),
        ),
        id="dissolve-frac-and-paren-unclosed-with-prefix",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="{1 + (2 + \\frac{3}{4} + 4 +5}",
            target_path=("node", 1, "_left_slot", 0),
            cursor_pos=0,
            expected_widget_cls_idx=[(0, BraceWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 5), (1, 2)],
            total_node_count=2,
            total_segment_count=10,
            total_edit_count=6,
            expected_plain_text="{1 + 2 + \\frac{3}{4} + 4 + 5}",
            expected_focus_cursor=(
                ("node", 1, "denominator", 0),
                1,
            ),  # xFail it should be (("node", 0, "_left_slot", 0), 4) it is going to DefaultFocus of fractionWidget
        ),
        id="dissolve-inner-paren-nested-paren",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="{1 + (2 + \\frac{3}{4} + 4) +5",
            target_path=("node", 0, "_left_slot", 0),
            cursor_pos=0,
            expected_widget_cls_idx=[(0, RoundParenWidget), (1, FractionWidget)],
            expected_inner_segments_idx=[(0, 5), (1, 2)],
            total_node_count=2,
            total_segment_count=10,
            total_edit_count=6,
            expected_plain_text="1 + (2 + \\frac{3}{4} + 4) + 5",
            expected_focus_cursor=(
                ("node", 1, "denominator", 0),
                1,
            ),  # xFail it should be (("root", 0), 0) it is going to DefaultFocus of fractionWidget
        ),
        id="dissolve-outer-paren-nested-paren",
    ),
    pytest.param(
        node_backspace_case(
            init_expr="{(2 + \\frac{3}{} + 4)+5}",
            target_path=("node", 2, "denominator", 0),
            cursor_pos=0,
            expected_widget_cls_idx=None,
            expected_inner_segments_idx=None,
            total_node_count=0,
            total_segment_count=1,
            total_edit_count=1,
            expected_plain_text="{(2 + 3 + 4 + 5)}",
            expected_focus_cursor=(("root", 0), 7),
        ),
        marks=pytest.mark.xfail(
            reason="nested paren, non ExpressionNode don't dissolve to outer paren"
        ),
        id="dissolve-frac-and-paren-nested-paren",
    ),
]


@pytest.mark.parametrize("rendered_case", NODE_BACKSPACE_CASES, indirect=True)
class TestNodeBackspace:
    """Test node removal via backspace on empty right slot."""

    @pytest.fixture(scope="class")
    def rendered_case(self, request, qapp):
        case = request.param
        widget = Expression()
        widget.show()
        widget.set_plain_text(case.init_expr)
        qapp.processEvents()

        t_before = snapshot_tree(widget)
        target = _resolve_target_input(widget, t_before, case.target_path)
        if not isinstance(target, QLineEdit):
            _fail_tree(
                widget,
                t_before,
                f"Expected QLineEdit target, got {type(target).__name__}",
            )

        _trigger_on_input(qapp, target, case.cursor_pos, widget.backspace)
        t_after = snapshot_tree(widget)

        yield case, widget, t_after

        widget.close()
        widget.deleteLater()
        qapp.processEvents()

    def test_node_classes(self, rendered_case):
        case, widget, t_after = rendered_case
        if case.expected_widget_cls_idx is None:
            return
        _check_indexed(
            widget,
            t_after,
            case.expected_widget_cls_idx,
            get_actual=lambda idx: type(t_after.all_nodes[idx].widget),
            label="node class",
            get_node=lambda idx: t_after.all_nodes[idx],
        )

    def test_node_segments(self, rendered_case):
        case, widget, t_after = rendered_case
        if case.expected_inner_segments_idx is None:
            return
        _check_indexed(
            widget,
            t_after,
            case.expected_inner_segments_idx,
            get_actual=lambda idx: sum(len(slot.segments) for slot in t_after.all_nodes[idx].slots),
            label="node segment count",
            get_node=lambda idx: t_after.all_nodes[idx],
        )

    def test_total_nodes(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            [(0, case.total_node_count)],
            get_actual=lambda _: len(t_after.all_nodes),
            label="total node count",
        )

    def test_total_segments(self, rendered_case):
        case, widget, t_after = rendered_case
        total_segments = sum(len(slot.segments) for slot in t_after.all_slots)
        _check_indexed(
            widget,
            t_after,
            [(0, case.total_segment_count)],
            get_actual=lambda _: total_segments,
            label="total segment count",
        )

    def test_total_edits(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            [(0, case.total_edit_count)],
            get_actual=lambda _: len(t_after.all_edits),
            label="total edit count",
        )

    def test_plain_text(self, rendered_case):
        case, widget, t_after = rendered_case
        _check_indexed(
            widget,
            t_after,
            [(0, case.expected_plain_text)],
            get_actual=lambda _: widget.get_plain_text(),
            label="plain text",
        )

    def test_focus_cursor(self, rendered_case):
        case, widget, t_after = rendered_case
        if case.expected_focus_cursor is None:
            return
        focus_path, expected_cursor = case.expected_focus_cursor
        expected_target = _resolve_target_input(widget, t_after, focus_path)
        actual_target = widget._resolve_target()
        if actual_target is not expected_target:
            expected_name = (
                expected_target.objectName()
                if isinstance(expected_target, QLineEdit)
                else type(expected_target).__name__
            )
            actual_name = (
                actual_target.objectName()
                if isinstance(actual_target, QLineEdit)
                else type(actual_target).__name__
            )
            _fail_tree(
                widget,
                t_after,
                f"Focus target mismatch: expected path {focus_path} ({expected_name}), got ({actual_name})",
            )
        _check_indexed(
            widget,
            t_after,
            [(0, expected_cursor)],
            get_actual=lambda _: actual_target.cursorPosition(),
            label="cursor position",
        )
