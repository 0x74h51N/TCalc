from __future__ import annotations

import pytest

from tcalc.ui.widgets.calc.display.expression.expression import Expression

SIMPLE_EXPR = "1/2"
MEDIUM_EXPR = "(1/2)/(3/4)"
COMPLEX_EXPR = "(((1/2)/(3/4))/(5/6))"
HEAVY_EXPR = (
    "((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))"
    "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
    "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))"
    "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
    "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
    "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10))))"
    "/((1+(2/(3+(4/5+6))))*(7-(8/(9+10)))))"
)
SICK_EXPR = (
    "((1^(2/(3^(4/(5^6)))))/(7^(8/(9^(10/11)))))"
    "/((2^(3/(4^(5/(6^7)))))/(8^(9/(10^(11/12)))))"
    "/((3^(4/(5^(6/(7^8)))))/(9^(10/(11^(12/13)))))"
    "/((4^(5/(6^(7/(8^9)))))/(10^(11/(12^(13/14)))))"
    "/((5^(6/(7^(8/(9^10)))))/(11^(12/(13^(14/15)))))"
    "/((6^(7/(8^(9/(10^11)))))/(12^(13/(14^(15/16)))))"
    "/((7^(8/(9^(10/(11^12)))))/(13^(14/(15^(16/17)))))"
)

# Regression thresholds ms
THRESHOLDS_MS = {"simple": 10, "medium": 20, "complex": 50, "heavy": 250, "sick": 500}


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "name,expr",
    [
        ("simple", SIMPLE_EXPR),
        ("medium", MEDIUM_EXPR),
        ("complex", COMPLEX_EXPR),
        ("heavy", HEAVY_EXPR),
        ("sick", SICK_EXPR),
    ],
    ids=["simple", "medium", "complex", "heavy", "sick"],
)
def test_expression_performance(qapp, benchmark, name: str, expr: str):
    """Test that expressionNode rendering stays under threshold."""
    threshold_ms = THRESHOLDS_MS[name]

    def render():
        widget = Expression()
        widget.show()
        widget.set_plain_text(expr)
        qapp.processEvents()
        widget.close()
        widget.deleteLater()
        qapp.processEvents()

    benchmark.pedantic(render, rounds=5, warmup_rounds=1)
    max_time_ms = benchmark.stats["max"] * 1000
    mean_time_ms = benchmark.stats["mean"] * 1000

    print(f"\n  {name}: {mean_time_ms:.1f}ms (max: {max_time_ms:.1f}ms, limit: {threshold_ms}ms)")

    assert max_time_ms < threshold_ms, (
        f"{name}: {max_time_ms:.1f}ms exceeds threshold={threshold_ms}ms"
    )
