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
    "simple": "\\frac{1}{2}",
    "medium": "\\frac{\\frac{1}{2}}{\\frac{2}{3}}",
    "complex": "\\frac{\\frac{\\frac{1}{2}}{\\frac{2}{3}}}{\\frac{5}{6}}",
    "heavy": (
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
    ),
    "sick": (
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{\\pow{1}{\\frac{2}{\\pow{3}{\\frac{4}{\\pow{5}{6}}}}}}"
        "{\\pow{7}{\\frac{8}{\\pow{9}{\\frac{10}{11}}}}}"
        "}"
        "{"
        "\\frac{\\pow{2}{\\frac{3}{\\pow{4}{\\frac{5}{\\pow{6}{7}}}}}}"
        "{\\pow{8}{\\frac{9}{\\pow{10}{\\frac{11}{12}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{3}{\\frac{4}{\\pow{5}{\\frac{6}{\\pow{7}{8}}}}}}"
        "{\\pow{9}{\\frac{10}{\\pow{11}{\\frac{12}{13}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{4}{\\frac{5}{\\pow{6}{\\frac{7}{\\pow{8}{9}}}}}}"
        "{\\pow{10}{\\frac{11}{\\pow{12}{\\frac{13}{14}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{5}{\\frac{6}{\\pow{7}{\\frac{8}{\\pow{9}{10}}}}}}"
        "{\\pow{11}{\\frac{12}{\\pow{13}{\\frac{14}{15}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{6}{\\frac{7}{\\pow{8}{\\frac{9}{\\pow{10}{11}}}}}}"
        "{\\pow{12}{\\frac{13}{\\pow{14}{\\frac{15}{16}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{7}{\\frac{8}{\\pow{9}{\\frac{10}{\\pow{11}{12}}}}}}"
        "{\\pow{13}{\\frac{14}{\\pow{15}{\\frac{16}{17}}}}}"
        "}"
        "}"
    ),
}

# Regression thresholds (ms)
THRESHOLDS_MS = {"simple": 10, "medium": 20, "complex": 50, "heavy": 150, "sick": 250}


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
