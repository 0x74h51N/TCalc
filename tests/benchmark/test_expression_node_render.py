"""Expression widget rendering benchmark tests.

Tests the performance of Expression widget's node creation and rendering.
Focus: FractionWidget/PowWidget creation from text input.
"""

from __future__ import annotations

import pytest

from tcalc.ui.widgets.calc.display.expression.expression import Expression

from .conftest import ROUNDS_RENDER, run_benchmark

# Test expressions - increasing complexity
EXPRESSIONS = {
    "simple": "1/2",
    "medium": "(1/2)/(3/4)",
    "complex": "(((1/2)/(3/4))/(5/6))",
    "heavy": (
        "((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))"
        "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
        "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))"
        "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
        "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
        "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))"
        "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
    ),
    "sick": (
        "((1^(2/(3^(4/(5^6)))))/(7^(8/(9^(10/11)))))"
        "/((2^(3/(4^(5/(6^7)))))/(8^(9/(10^(11/12)))))"
        "/((3^(4/(5^(6/(7^8)))))/(9^(10/(11^(12/13)))))"
        "/((4^(5/(6^(7/(8^9)))))/(10^(11/(12^(13/14)))))"
        "/((5^(6/(7^(8/(9^10)))))/(11^(12/(13^(14/15)))))"
        "/((6^(7/(8^(9/(10^11)))))/(12^(13/(14^(15/16)))))"
        "/((7^(8/(9^(10/(11^12)))))/(13^(14/(15^(16/17)))))"
    ),
}

# Regression thresholds (ms)
THRESHOLDS_MS = {"simple": 10, "medium": 20, "complex": 50, "heavy": 250, "sick": 500}


def _make_render_func(qapp, expr: str):
    def render():
        widget = Expression()
        widget.show()
        widget.set_plain_text(expr)
        qapp.processEvents()
        widget.close()
        widget.deleteLater()
        qapp.processEvents()

    return render


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_expression_render_benchmark(qapp, benchmark, name: str):
    """Test that Expression widget rendering stays under threshold."""
    run_benchmark(
        benchmark,
        _make_render_func(qapp, EXPRESSIONS[name]),
        group="Expression Node Widgets' Render",
        name=name,
        threshold_ms=THRESHOLDS_MS[name],
        rounds=ROUNDS_RENDER,
    )
