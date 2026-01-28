from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from tcalc.ui.widgets.calc.display.expression.expression import Expression

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

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

# Regression thresholds ms
THRESHOLDS_MS = {
    "simple": 50,
    "medium": 50,
    "complex": 100,
    "heavy": 400,
}


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "name,expr",
    [
        ("simple", SIMPLE_EXPR),
        ("medium", MEDIUM_EXPR),
        ("complex", COMPLEX_EXPR),
        ("heavy", HEAVY_EXPR),
    ],
    ids=["simple", "medium", "complex", "heavy"],
)
def test_expression_performance(qapp, request: pytest.FixtureRequest, name: str, expr: str):
    """Test that expressionNode rendering stays under threshold."""
    threshold_ms = THRESHOLDS_MS[name]
    max_time_ms = 0.0

    def render():
        widget = Expression()
        widget.show()
        widget.set_plain_text(expr)
        qapp.processEvents()
        widget.close()
        widget.deleteLater()
        qapp.processEvents()

    benchmark: BenchmarkFixture | None = None
    try:
        benchmark = request.getfixturevalue("benchmark")
    except pytest.FixtureLookupError:
        pass

    if benchmark is None or benchmark.disabled:
        start = time.perf_counter()
        render()
        max_time_ms = (time.perf_counter() - start) * 1000
        mean_time_ms = max_time_ms
    else:
        benchmark.pedantic(render, rounds=5, warmup_rounds=1)
        max_time_ms = benchmark.stats["max"] * 1000
        mean_time_ms = benchmark.stats["mean"] * 1000

    print(f"\n  {name}: {mean_time_ms:.1f}ms (max: {max_time_ms:.1f}ms, limit: {threshold_ms}ms)")

    assert max_time_ms < threshold_ms, (
        f"{name}: {max_time_ms:.1f}ms exceeds threshold={threshold_ms}ms"
    )
