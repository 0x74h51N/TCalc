"""Memory allocation benchmarks for expression rendering and native C++ code."""

from __future__ import annotations

import calc_native
import pytest

from tcalc.core.engine import Calculator
from tcalc.core.parser import evaluate_tokens, tokenize_string
from tcalc.ui.widgets.calc.display.expression.expression import Expression
from tcalc.ui.window import MainWindow
from tests.benchmark.expressions import PIPELINE_EXPRESSIONS, RENDER_EXPRESSIONS


@pytest.mark.benchmark
def test_app_baseline_memory(qapp):
    window = MainWindow()
    window.show()
    qapp.processEvents()


@pytest.mark.benchmark
def test_expression_baseline_memory(qapp):
    w = Expression()
    w.show()
    qapp.processEvents()


def _render_once(qapp, expr: str):
    widget = Expression()
    widget.show()
    widget.set_plain_text(expr)
    qapp.processEvents()
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_expression_render_memory(qapp, name: str):
    _render_once(qapp, RENDER_EXPRESSIONS[name])


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_app_render_memory(qapp, name: str):
    """Full app + expression render: MainWindow + Expression widget + expression render."""
    window = MainWindow()
    window.show()
    qapp.processEvents()
    display = window.calc_widget.display
    display.editor.set_plain_text(RENDER_EXPRESSIONS[name])
    qapp.processEvents()


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_native_tokenize_memory(name: str):
    """Measure C++ tokenizer allocations (std::vector<Token>, std::string)."""
    calc_native.tokenize_string(PIPELINE_EXPRESSIONS[name])


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_native_shunting_yard_memory(name: str):
    """Measure C++ shunting-yard allocations."""
    tokens = tokenize_string(PIPELINE_EXPRESSIONS[name])
    calc_native.shunting_yard(tokens)


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_native_pipeline_memory(name: str):
    """Measure full native pipeline: tokenize -> shunting-yard -> evaluate."""
    calc = Calculator()
    tokens = tokenize_string(PIPELINE_EXPRESSIONS[name])
    evaluate_tokens(tokens, calc)
