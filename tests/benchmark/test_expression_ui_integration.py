"""Expression UI integration benchmark tests.

Measures incremental edit performance: after initial render,
how fast do individual QLineEdit changes propagate through the pipeline.
"""

from __future__ import annotations

import pytest

from tcalc.ui.widgets.calc.display.expression.expression import Expression

from .conftest import ROUNDS_RENDER, run_benchmark
from .test_expression_node_render import EXPRESSIONS


def _setup_widget(qapp, expr: str) -> Expression:
    """Create and render a widget."""
    widget = Expression()
    widget.show()
    widget.set_plain_text(expr)
    qapp.processEvents()
    return widget


def _make_incremental_edit_func(qapp, widget: Expression):
    edits = widget.expression_inputs()
    step = [0]

    def edit_step():
        if not edits:
            return
        target = edits[step[0] % len(edits)]
        text = target.text()

        if text.endswith("1") and len(text) > 1:
            target.setText(text[:-1])
        else:
            target.setText(text + "1")
        qapp.processEvents()

    return edit_step


def _make_multi_edit_func(qapp, widget: Expression, num_steps: int = 5):
    edits = widget.expression_inputs()

    def multi_edit():
        if not edits:
            return
        for i in range(min(num_steps, len(edits))):
            target = edits[i]
            text = target.text()
            if text.endswith("1") and len(text) > 1:
                target.setText(text[:-1])
            else:
                target.setText(text + "1")
        qapp.processEvents()

    return multi_edit


SINGLE_EDIT_THRESHOLDS_MS = {
    "simple": 5,
    "medium": 5,
    "complex": 10,
    "heavy": 15,
    "sick": 25,
}

MULTI_EDIT_THRESHOLDS_MS = {
    "simple": 5,
    "medium": 10,
    "complex": 20,
    "heavy": 50,
    "sick": 100,
}


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_single_edit_benchmark(qapp, benchmark, name: str):
    widget = _setup_widget(qapp, EXPRESSIONS[name])
    try:
        run_benchmark(
            benchmark,
            _make_incremental_edit_func(qapp, widget),
            group="Expression UI Integration — Single Edit",
            name=name,
            threshold_ms=SINGLE_EDIT_THRESHOLDS_MS[name],
            rounds=ROUNDS_RENDER,
        )
    finally:
        widget.close()
        widget.deleteLater()
        qapp.processEvents()


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_multi_edit_benchmark(qapp, benchmark, name: str):
    widget = _setup_widget(qapp, EXPRESSIONS[name])
    try:
        run_benchmark(
            benchmark,
            _make_multi_edit_func(qapp, widget, num_steps=5),
            group="Expression UI Integration — Multi Edit (5 steps)",
            name=name,
            threshold_ms=MULTI_EDIT_THRESHOLDS_MS[name],
            rounds=ROUNDS_RENDER,
        )
    finally:
        widget.close()
        widget.deleteLater()
        qapp.processEvents()
